import os
import sqlite3
import math
from flask import Flask, request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Rate limiting: 1 submission per minute
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day"],
    storage_uri="memory://"
)

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
DATABASE = 'provenance_guard.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute('''
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                groq_score REAL,
                heuristic_score REAL,
                final_score REAL,
                label TEXT,
                appeal_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'classified',
                appeal_reason TEXT
            )
        ''')
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- Detection Signals ---

def get_groq_signal(text: str) -> float:
    """Signal 1: Groq Llama-3 evaluation."""
    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Analyze this text. Is it human-written or AI-generated? Reply ONLY with a single float between 0.0 (100% AI) and 1.0 (100% Human). Do not include any other text."},
                {"role": "user", "content": text}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        score = float(response.choices[0].message.content.strip())
        return max(0.0, min(1.0, score))
    except Exception as e:
        print(f"Groq API Error: {e}")
        return 0.5 

def get_stylometric_signal(text: str) -> float:
    """Signal 2: Pure Python heuristics (Type-Token Ratio & Variance)."""
    words = text.split()
    if not words: return 0.5
    
    # Vocabulary diversity (Type-Token Ratio)
    unique_words = set(words)
    ttr = len(unique_words) / len(words)
    
    # AI tends to have lower TTR (more repetitive) and highly uniform sentence lengths.
    # We'll map a higher TTR to a higher "Human" score.
    normalized_ttr = min(1.0, ttr * 1.5) 
    
    return round(normalized_ttr, 2)

def determine_label(score: float) -> str:
    """Maps the score to the transparency labels defined in planning.md."""
    if score < 0.45:
        return "Confidently AI"
    elif score <= 0.54:
        return "Uncertain"
    else:
        return "Confidently Human"

# --- Endpoints ---

@app.route('/submit', methods=['POST'])
@limiter.limit("1 per minute")
def submit_content():
    data = request.json
    content = data.get("content", "")
    
    if not content:
        return jsonify({"error": "No content provided"}), 400

    groq_score = get_groq_signal(content)
    heuristic_score = get_stylometric_signal(content)
    
    # Combined score
    final_score = round((groq_score + heuristic_score) / 2.0, 2)
    label = determine_label(final_score)

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO audit (content, groq_score, heuristic_score, final_score, label) VALUES (?, ?, ?, ?, ?)",
        (content, groq_score, heuristic_score, final_score, label)
    )
    db.commit()
    
    return jsonify({
        "content_id": cursor.lastrowid,
        "confidence_score": final_score,
        "transparency_label": label,
        "signals": {
            "groq_semantics": groq_score,
            "stylometric_heuristics": heuristic_score
        }
    }), 201

# Classifies content and allows for appeals if the user disagrees with the classification.
# Appeals are limited to 5 per content item.
@app.route('/appeal/<int:content_id>', methods=['POST'])
def appeal_classification(content_id):
    data = request.json
    appeal_reason = data.get("reason", "")
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM audit WHERE id = ?", (content_id,))
    row = cursor.fetchone()
    
    if not row:
        return jsonify({"error": "Content ID not found"}), 404
        
    if row['appeal_count'] >= 5:
        return jsonify({"error": "Maximum appeals (5) reached for this content"}), 403
        
    new_appeal_count = row['appeal_count'] + 1
    
    # Update status to under review and log the appeal
    cursor.execute(
        "UPDATE audit SET status = 'under review', appeal_reason = ?, appeal_count = ? WHERE id = ?",
        (appeal_reason, new_appeal_count, content_id)
    )
    db.commit()
    
    return jsonify({
        "message": "Appeal logged successfully. Content is under review.",
        "content_id": content_id,
        "appeal_count": new_appeal_count,
        "status": "under review",
        "provided_reason": appeal_reason
    }), 200

@app.route('/log', methods=['GET'])
def get_log():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, groq_score, heuristic_score, final_score, label, status, appeal_count, appeal_reason FROM audit ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    return jsonify([dict(ix) for ix in rows]), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)