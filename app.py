from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import timedelta
import os
from db import *
from colors_test import get_dominant_color, _closest_color_name, generate_outfit_suggestions
from PIL import Image

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config.update(
    SECRET_KEY= app.secret_key,
    SESSION_COOKIE_SECURE=True,       # HTTPS only
    SESSION_COOKIE_HTTPONLY=True,    # Prevent JS access
    SESSION_COOKIE_SAMESITE='Lax',   # CSRF protection
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),  # For remember me
    REMEMBER_COOKIE_SECURE=True,
    REMEMBER_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_DURATION=timedelta(days=30),
    REMEMBER_COOKIE_NAME='wardrobe_remember'
)

# Initialize security extensions
csrf = CSRFProtect(app)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

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
        username = validate_user(identifier, password)
        remember_me = request.form.get('remember_me') == 'on'
        if username:
            session['username'] = username
            session['wardrobe_id'] = get_wardrobe_id(identifier)
            session.permanent = remember_me
            flash(f"Logged in as {username}.", "info")
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
            create_user(email=email, username=username, password=password)
            flash("Account created. Please log in.", "info")
            return redirect(url_for('login'))
        except Exception as e:
            print(e)
            flash("Username or email already exists", "danger")
    return render_template('signup.html')

@app.route('/wardrobe', methods=['GET', 'POST'])
def wardrobe():
    if 'username' not in session:
        return redirect('/')
    items = fetch_wardrobe_items(session['wardrobe_id'])
    return render_template('wardrobe.html', items=items, username=session['username'], closest_color_name= _closest_color_name)

@app.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session:
        return redirect('/')
    
    if 'image' not in request.files or 'category' not in request.form:
        flash("Image and category are required", "danger")
        return redirect(url_for('wardrobe'))

    file = request.files['image']
    category = request.form['category']
    filename = secure_filename(file.filename)
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)

    image = Image.open(path).convert('RGB')
    rgb = get_dominant_color(image)
    insert_clothing_item(session['wardrobe_id'], category, rgb)
    name = _closest_color_name(rgb)
    flash(f"Added {name} {rgb} to {category}", "success")
    return redirect(url_for('wardrobe'))

@app.route('/delete/<int:item_id>', methods=['POST'])
def delete(item_id):
    delete_clothing_item(item_id)
    return redirect(url_for('wardrobe'))

@app.route('/generate')
def generate():
    if 'username' not in session:
        return redirect('/')
    wardrobe = fetch_wardrobe_items(session['wardrobe_id'])
    outfits = generate_outfit_suggestions({k: [i['rgb'] for i in v] for k, v in wardrobe.items()})
    return render_template('outfits.html', outfits=outfits, closest_color_name= _closest_color_name)

@app.route('/save_outfit', methods=['POST'])
def save_outfit_route():
    try:
        t = eval(request.form['top'])
        p = eval(request.form['pants'])
        s = eval(request.form['shoes'])
        j = eval(request.form.get('jacket')) if request.form.get('jacket') else None
        score = float(request.form['score'])
    except:
        flash("Invalid outfit data", "danger")
        return redirect(url_for('generate'))

    top_id = get_item_id_by_color(session['wardrobe_id'], 'tops', t)
    pants_id = get_item_id_by_color(session['wardrobe_id'], 'pants', p)
    shoes_id = get_item_id_by_color(session['wardrobe_id'], 'shoes', s)
    jacket_id = get_item_id_by_color(session['wardrobe_id'], 'jackets', j) if j else None

    save_outfit(session['wardrobe_id'], top_id, pants_id, shoes_id, jacket_id, score)
    flash("Outfit saved!", "success")
    return redirect(url_for('generate'))

@app.route('/saved')
def saved():
    if 'username' not in session:
        return redirect('/')
    outfits = fetch_saved_outfits(session['wardrobe_id'])
    return render_template('outfits.html', outfits=outfits, saved=True, closest_color_name= _closest_color_name)

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True, port=5002, host='0.0.0.0')
