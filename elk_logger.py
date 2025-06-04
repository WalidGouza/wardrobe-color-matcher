from elasticsearch import Elasticsearch
from datetime import datetime

# Set up Elasticsearch connection
es = Elasticsearch("http://elasticsearch:9200")

def log_outfit_to_elasticsearch(outfit: dict, user: dict = None):
    doc = {
        "user": user["username"] if user else "anonymous",
        "timestamp": datetime.utcnow().isoformat(),
        "top_rgb": outfit["top"]["rgb"],
        "pants_rgb": outfit["pants"]["rgb"],
        "shoes_rgb": outfit["shoes"]["rgb"],
        "jacket_rgb": outfit["jacket"]["rgb"] if outfit["jacket"] else None,
        "score": outfit["score"]
    }
    try:
        es.index(index="outfit-logs", document=doc)
    except Exception as e:
        print(f"[ELK] Error logging outfit: {e}")

def log_login_to_elasticsearch(user=None, ip=None):
    doc = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_username": user.username,
        "user_email": user.email,
        "user_ip": ip,
    }
    
    try:
        es.index(index="login-logs", document=doc)
    except Exception as e:
        print(f"[ELK] Error logging user: {e}")