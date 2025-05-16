import psycopg2
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

DB_CONFIG = {
    'host': DB_HOST,
    'port': DB_PORT,
    'dbname': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD
}

def create_user(email, username, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users (email, username, password) VALUES (%s, %s, %s)", (email, username, hashed))
            cur.execute("SELECT id FROM users WHERE username = %s AND email = %s", (username, email))
            user_id = cur.fetchone()

            # Create wardrobe
            cur.execute("INSERT INTO wardrobe (user_id) VALUES (%s)", (user_id,))

def validate_user(identifier, password):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT username, password FROM users WHERE username = %s OR email = %s", (identifier, identifier))
            row = cur.fetchone()
            if row:
                username, hashed_pw = row
                if bcrypt.checkpw(password.encode(), hashed_pw.encode()):
                    return username
    return None

def get_wardrobe_id(username):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT w.id
                FROM wardrobe w
                JOIN users u ON w.user_id = u.id
                WHERE u.username = %s
            """, (username,))
            row = cur.fetchone()
            return row[0] if row else None


def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def insert_clothing_item(wardrobe_id, clothing_type, rgb):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO clothing_items (wardrobe_id, type, r, g, b)
                VALUES (%s, %s, %s, %s, %s)
            """, (wardrobe_id, clothing_type, rgb[0], rgb[1], rgb[2]))

def fetch_wardrobe_items(wardrobe_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, type, r, g, b
                FROM clothing_items
                WHERE wardrobe_id = %s
                ORDER BY type
            """, (wardrobe_id,))
            rows = cur.fetchall()
    
    wardrobe = {'tops': [], 'pants': [], 'shoes': [], 'jackets': []}
    for item_id, clothing_type, r, g, b in rows:
        if clothing_type in wardrobe:
            rgb = (int(r), int(g), int(b))
            wardrobe[clothing_type].append({'id': item_id, 'rgb': (r, g, b)})
    return wardrobe

def save_outfit(wardrobe_id, top_id, pant_id, shoe_id, jacket_id, score):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1 FROM Outfit
                WHERE wardrobe_id = %s
                AND top_id = %s
                AND pant_id = %s
                AND shoe_id = %s
                AND (jacket_id = %s OR (jacket_id IS NULL AND %s IS NULL))
            """, (wardrobe_id, top_id, pant_id, shoe_id, jacket_id, jacket_id))

            if cur.fetchone():
                return False # Duplicate exists; skip saving

            cur.execute("""
                INSERT INTO Outfit (wardrobe_id, top_id, pant_id, shoe_id, jacket_id, score)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (wardrobe_id, top_id, pant_id, shoe_id, jacket_id, score))
            conn.commit()
            return True # Successfully saved
        
def get_item_id_by_color(wardrobe_id, clothing_type, rgb):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM clothing_items
                WHERE wardrobe_id = %s AND type = %s AND r = %s AND g = %s AND b = %s
                LIMIT 1
            """, (wardrobe_id, clothing_type, rgb[0], rgb[1], rgb[2]))
            row = cur.fetchall()
            return row[0] if row else None
            
def fetch_saved_outfits(wardrobe_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT top_id, pant_id, shoe_id, jacket_id, score
                FROM Outfit
                WHERE wardrobe_id = %s
            """, (wardrobe_id,))
            rows = cur.fetchall()

    outfits = []
    for top_id, pant_id, shoe_id, jacket_id, score in rows:
        outfit = []
        for item_id in [top_id, pant_id, shoe_id, jacket_id]:
            if item_id is None:
                outfit.append(None)
                continue
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT r, g, b FROM clothing_items
                        WHERE id = %s
                    """, (item_id,))
                    row = cur.fetchone()
                    outfit.append((int(row[0]), int(row[1]), int(row[2])) if row else None)
        outfits.append((*outfit, score))
    return outfits


def delete_clothing_item(item_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM clothing_items WHERE id = %s", (item_id,))
