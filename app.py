from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from email_validator import validate_email, EmailNotValidError
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from datetime import timedelta
import os
from db import *
from colors_test import suggest_outfit_for_item, get_dominant_color, _closest_color_name, generate_outfit_suggestions
from PIL import Image
import random
from datetime import date

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config.update(
    # SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_DOMAIN= '192.168.1.22',    # LAN Domain for cross device acces
    SESSION_COOKIE_HTTPONLY=True,    # Prevent JS access
    SESSION_COOKIE_SAMESITE='Lax',   # CSRF protection
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),  # For remember me
    REMEMBER_COOKIE_SECURE=True,
    REMEMBER_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_DURATION=timedelta(days=30),
    REMEMBER_COOKIE_NAME='wardrobe_remember',
)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get("MAIL_USERNAME")

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

mail = Mail(app)
s = URLSafeTimedSerializer(app.secret_key)

class User():
    def __init__(self, id, username, email, wardrobe_id, profile_pic):
        self.id = id
        self.username = username
        self.email = email
        self.wardrobe_id = wardrobe_id
        self.profile_pic = profile_pic or "profile_pic_default.png"
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'wardrobe_id': self.wardrobe_id,
            'profile_pic': self.profile_pic
        }

    @staticmethod
    def from_dict(data):
        return User(
            id=data['id'],
            username=data['username'],
            email=data['email'],
            wardrobe_id=data['wardrobe_id'],
            profile_pic=data.get('profile_pic', 'profile_pic_default.png')
        )

def send_confirmation_email(email, username):
    token = s.dumps(email, salt='email-confirm')
    confirm_url = url_for('confirm_email', token=token, _external=True)

    msg = Message(
        subject="Confirm Your Account",
        recipients=[email],
        body=f"Hi {username}, confirm your account: {confirm_url}"
    )
    mail.send(msg)

def send_welcome_email(username, email):
    msg = Message(
        subject=f"Hi {username}, Welcome to Smart Wardrobe",
        recipients=[email],
        body=f"""Hi {username}, \n🎉 Welcome to Smart Wardrobe!
                Your account is now active. Start building your wardrobe and discover perfect outfits tailored by color and style.
                Let's make getting dressed effortless!
        """)
    mail.send(msg)

# Initialize security extensions
csrf = CSRFProtect(app)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per hour", methods=['POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier'].strip()
        password = request.form['password']
        info = validate_user(identifier, password)
        
        if info:
            wardrobe_id = get_wardrobe_id(info[1])

            user = User(
                id=info[0],
                username=info[1],
                email=info[3],
                wardrobe_id=wardrobe_id,
                profile_pic=info[5]
            )

            session['user'] = user.to_dict()
            flash(f"Logged in as {user.username}.", "info")
            return redirect(url_for('home'))
        else:
            flash("Invalid credentials", "danger")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        email = request.form.get('email','').strip().lower()
        
        try:
            valid = validate_email(email)
            email = valid.email
            
        except EmailNotValidError as e:
            flash(str(e), "danger")
            return redirect(url_for('signup'))
        
        try:
            create_user(email=email, username=username, password=password)
        
            send_confirmation_email(email, username)
            
            flash("Account created. Please check your inbox and confirm your email", "info")
        except Exception:
            flash("Username or email already exists", "danger")
    return render_template('signup.html')

@app.route('/account')
def account():
    return render_template('account.html', session=session)

@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
        username = mark_user_as_confirmed(email)
        flash("✅ Email confirmed successfully!", "success")
        send_welcome_email(username, email)
        return redirect(url_for('login'))
    except Exception:
        flash("Invalid or expired confirmation link.", "danger")
        return redirect(url_for('signup'))

@app.route('/edit-profile', methods=['POST'])
def edit_profile():
    if 'user' not in session:
        flash("Please log in.", "warning")
        return redirect(url_for('login'))

    user = User.from_dict(session['user'])
    new_username = request.form.get('username', '').strip()
    new_password = request.form.get('password', '').strip()
    file = request.files.get('profile_pic')

    profile_pic_filename = user.profile_pic  # default to current

    if file and allowed_file(file.filename):
        filename = secure_filename(f"user_{user.id}.{file.filename.rsplit('.', 1)[1].lower()}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        profile_pic_filename = filename

    try:
        update_user_account(
            user_id=user.id,
            username=new_username if new_username != user.username else None,
            password=new_password if new_password else None,
            profile_pic=profile_pic_filename
        )

        # refresh session
        user.username = new_username
        user.profile_pic = profile_pic_filename
        session['user'] = user.to_dict()

        flash("✅ Profile updated successfully.", "success")
    except Exception as e:
        print("Update error:", e)
        flash("❌ Failed to update profile.", "danger")

    return redirect(url_for('account'))

@app.route('/delete-account', methods=['POST'])
def delete_account():
    if 'user' not in session:
        flash("You're not logged in.", "warning")
        return redirect(url_for('login'))

    username = session['user']['username']
    delete_user_account(username)
    session.clear()
    flash("Your account has been permanently deleted.", "info")
    return redirect(url_for('signup'))


@app.route('/wardrobe')
def wardrobe():
    if 'user' not in session:
        flash("Please log in.", "warning")
        return redirect(url_for('login'))
    user = User.from_dict(session['user'])
    items = fetch_wardrobe_items(user.wardrobe_id)
    return render_template('wardrobe.html', items=items, username=user.username, closest_color_name=_closest_color_name)


@app.route('/upload', methods=['POST'])
def upload():
    if 'user' not in session:
        flash("Please log in to upload items.", "warning")
        return redirect(url_for('login'))

    # Validate form
    file = request.files.get('image')
    category = request.form.get('category')
    if not file or not category:
        flash("Image and category are required.", "danger")
        return redirect(url_for('wardrobe'))

    # Check file extension
    if not allowed_file(file.filename):
        flash("Invalid file type. Please upload a .jpg, .jpeg, or .png image.", "danger")
        return redirect(url_for('wardrobe'))

    user = User.from_dict(session['user'])

    # Generate safe and unique filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    raw_name = secure_filename(file.filename.rsplit('.', 1)[0])
    filename = secure_filename(f"{category}_{user.id}_{raw_name}.{ext}")
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    # Extract dominant color
    try:
        image = Image.open(file_path).convert('RGB')
        rgb = get_dominant_color(image)
    except Exception as e:
        print("Image processing error:", e)
        flash("Failed to process the image.", "danger")
        return redirect(url_for('wardrobe'))

    # Save to DB with filename
    try:
        insert_clothing_item(user.wardrobe_id, category, rgb, filename)
        color_name = _closest_color_name(rgb)
        flash(f"✅ Added {color_name} {rgb} to {category}.", "success")
    except Exception as e:
        print("Database insert error:", e)
        flash("❌ Failed to save clothing item.", "danger")

    return redirect(url_for('wardrobe'))

@app.route('/delete/<int:item_id>', methods=['POST'])
def delete(item_id):
    delete_clothing_item(item_id)
    return redirect(url_for('wardrobe'))

@app.route('/generate')
def generate():
    if 'user' not in session:
        return redirect('/')
    wardrobe = fetch_wardrobe_items(session['user']['wardrobe_id'])
    outfits = generate_outfit_suggestions(wardrobe)
    print(wardrobe)
    return render_template('outfits.html', outfits=outfits, closest_color_name= _closest_color_name)

@app.route('/generate-item/<int:item_id>', methods=['POST'])
def generate_item(item_id):
    if 'user' not in session:
        return redirect('/')
    
    wardrobe = fetch_wardrobe_items(session['user']['wardrobe_id'])
    user_input = {}
    
    for type, items in wardrobe.items():
        for item in items:
            if item['id'] == item_id:
                rgb = item['rgb']
                item_type = type
                user_input = {
                    item_type: rgb
                }
    
    outfits = suggest_outfit_for_item(user_input, wardrobe)
    return render_template('outfits.html', outfits=outfits, closest_color_name= _closest_color_name, user_input=user_input)

@app.route('/ootd')
def ootd():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = User.from_dict(session['user'])
    wardrobe = fetch_wardrobe_items(user.wardrobe_id)
    outfits = generate_outfit_suggestions(wardrobe)

    if not outfits:
        flash("No saved outfits yet!", "warning")
        return redirect(url_for('wardrobe'))

    # Pick one outfit per day based on the date
    random.seed(date.today().isoformat())
    selected_outfit = random.choice(outfits)
    return render_template('ootd.html', selected_outfit=selected_outfit)

@app.route('/save_outfit', methods=['POST'])
def save_outfit_route():
    if 'user' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))
    
    try:
        t = eval(request.form['top'])
        p = eval(request.form['pants'])
        s = eval(request.form['shoes'])
        j = eval(request.form.get('jacket')) if request.form.get('jacket') else None
        score = float(request.form['score'])
    except:
        flash("Invalid outfit data", "danger")
        return redirect(url_for('generate'))

    top_id = get_item_id_by_color(session['user']['wardrobe_id'], 'tops', t)
    pants_id = get_item_id_by_color(session['user']['wardrobe_id'], 'pants', p)
    shoes_id = get_item_id_by_color(session['user']['wardrobe_id'], 'shoes', s)
    jacket_id = get_item_id_by_color(session['user']['wardrobe_id'], 'jackets', j) if j else None

    save_outfit(session['user']['wardrobe_id'], top_id, pants_id, shoes_id, jacket_id, score)
    flash("Outfit saved!", "success")
    return redirect(url_for('generate'))

@app.route('/saved')
def saved():
    if 'user' not in session:
        return redirect('/')
    outfits = fetch_saved_outfits(session['user']['wardrobe_id'])
    return render_template('outfits.html', outfits=outfits, saved=True, closest_color_name= _closest_color_name)

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True, port=5002, host='0.0.0.0')
