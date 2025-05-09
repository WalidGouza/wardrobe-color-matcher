# 👕 Wardrobe Color Matcher

This is a Python GUI app that helps colorblind users build well-matched outfits using color theory.

Users can upload images of clothing items, extract dominant colors, and receive outfit suggestions based on complementary, analogous, and neutral color relationships.

---

## 🎯 Features

- Upload clothing item images
- Automatically extract dominant colors
- Classify items as tops, pants, shoes, or jackets
- Store wardrobe data in a PostgreSQL database
- Generate and score outfit combinations
- View and delete clothing items
- Save everything using a clean, persistent backend

---

## 🧱 Tech Stack

- Python 3
- Tkinter (GUI)
- Pillow (image handling)
- psycopg2 (PostgreSQL)
- webcolors (color naming)
- PostgreSQL (data storage)
- VSCode + Git + GitHub

---

## 🚀 Getting Started

### 1. Clone the repo:

```bash
git clone https://github.com/WalidGouza/wardrobe-color-matcher.git 
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up the database
Use `wardrobe.sql` to create the tables in PostgreSQL

Update `db.py` with your DB credentials

### 4. Run the app
```bash
python gui.py
```
---

## 📂 Folder Structure
│
├── colors_test.py     # Outfit scoring and color logic
├── db.py              # Database functions
├── gui.py             # Tkinter GUI
├── wardrobe.sql       # DB schema
├── README.md

---

## 🙋‍♂️ Author
Walid Gouza – @WalidGouza