from flask import Flask, request, jsonify
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from omr_processing.omr_core import load_image, correct_orientation, save_image, detect_bubble_grid, detect_filled_bubbles, load_answer_key
import numpy as np
import sqlite3
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = 'data/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'omr_results.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        score INTEGER,
        total INTEGER,
        timestamp TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        action TEXT,
        timestamp TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

@app.route('/process', methods=['POST'])
def process_omr():
    # Expect image file and answer key path, rows, cols
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    image_file = request.files['image']
    rows = int(request.form.get('rows', 5))
    cols = int(request.form.get('cols', 20))
    answer_key_path = request.form.get('answer_key', 'answer_keys/SetA_key.csv')
    img_path = os.path.join(UPLOAD_FOLDER, image_file.filename)
    image_file.save(img_path)
    try:
        img = load_image(img_path)
        rectified, angle = correct_orientation(img)
        grid_img, grid_coords = detect_bubble_grid(rectified)
        bubble_matrix = detect_filled_bubbles(grid_img, rows, cols)
        answer_key = load_answer_key(answer_key_path, rows, cols)
        score = int(np.sum(bubble_matrix == answer_key))
        result = {
            'rotation_angle': angle,
            'grid_coords': grid_coords,
            'bubble_matrix': bubble_matrix.tolist(),
            'score': score,
            'total': rows * cols
        }
        # Save result to DB
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT INTO results (filename, score, total, timestamp) VALUES (?, ?, ?, ?)',
                  (image_file.filename, score, rows * cols, datetime.now().isoformat()))
        c.execute('INSERT INTO audit_log (filename, action, timestamp) VALUES (?, ?, ?)',
                  (image_file.filename, 'processed', datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/", methods=["GET"])
def status():
    return "OMR Backend Server is running!", 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)