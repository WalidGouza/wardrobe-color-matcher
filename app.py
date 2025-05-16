from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.utils import secure_filename
import os
from db import *
from colors_test import get_dominant_color, _closest_color_name, generate_outfit_suggestions
from PIL import Image

app = Flask(__name__)
app.secret_key = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier'].strip()
        password = request.form['password']
        username = validate_user(identifier, password)
        if username:
            session['username'] = username
            session['wardrobe_id'] = get_wardrobe_id(identifier)
            flash(f"Logged in as {username}.", "info")
            return redirect(url_for('wardrobe'))
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
    if 'identifier' not in session:
        return redirect('/')
    items = fetch_wardrobe_items(session['wardrobe_id'])
    return render_template('wardrobe.html', items=items, username=session['username'], closest_color_name= _closest_color_name)

@app.route('/upload', methods=['POST'])
def upload():
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
    t = eval(request.form['top'])
    p = eval(request.form['pants'])
    s = eval(request.form['shoes'])
    j = eval(request.form.get('jacket')) if request.form.get('jacket') else None
    score = float(request.form['score'])

    top_id = get_item_id_by_color(session['wardrobe_id'], 'tops', t)
    pants_id = get_item_id_by_color(session['wardrobe_id'], 'pants', p)
    shoes_id = get_item_id_by_color(session['wardrobe_id'], 'shoes', s)
    jacket_id = get_item_id_by_color(session['wardrobe_id'], 'jackets', j) if j else None

    save_outfit(session['wardrobe_id'], top_id, pants_id, shoes_id, jacket_id, score)
    flash("Outfit saved!", "success")
    return redirect(url_for('generate'))

@app.route('/saved')
def saved():
    outfits = fetch_saved_outfits(session['wardrobe_id'])
    return render_template('outfits.html', outfits=outfits, saved=True, closest_color_name= _closest_color_name)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True, port=5002)
