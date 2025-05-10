import psycopg2
import bcrypt

DB_CONFIG = {
    'dbname': 'wardrobe_db',
    'user': 'gouzaw',
    'password': 'walid2004',
    'host': 'localhost',
    'port': '5432',
}

def create_user(username, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
            user_id = cur.fetchone()[0]

            # Create wardrobe
            cur.execute("INSERT INTO wardrobe (user_id) VALUES (%s)", (user_id,))

def validate_user(username, password):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT password FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
            if row and bcrypt.checkpw(password.encode(), row[0].encode()):
                return True
    return False

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

def delete_clothing_item(item_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM clothing_items WHERE id = %s", (item_id,))
