from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'history_db'
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

@app.route('/api/history/ping', methods=['GET'])
def ping():
    return jsonify({
        "status": "ok",
        "service": "history",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT user_id, chapter_id, created_at FROM reading_history ORDER BY created_at DESC")
        history = cursor.fetchall()

        cursor.close()
        connection.close()

        return jsonify({"history": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/history/user/<int:user_id>', methods=['GET'])
def get_user_history(user_id):
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT user_id, chapter_id, created_at FROM reading_history WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        history = cursor.fetchall()

        cursor.close()
        connection.close()

        return jsonify({"history": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/history', methods=['POST'])
def add_to_history():
    try:
        data = request.get_json()
        if not data or 'user_id' not in data or 'chapter_id' not in data:
            return jsonify({"error": "Missing required fields"}), 400

        user_id = data['user_id']
        chapter_id = data['chapter_id']

        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = connection.cursor()
        
        try:
            # Try to insert new entry
            cursor.execute("INSERT INTO reading_history (user_id, chapter_id) VALUES (%s, %s)",
                         (user_id, chapter_id))
        except mysql.connector.IntegrityError:
            # If entry exists, update the timestamp
            cursor.execute("UPDATE reading_history SET created_at = CURRENT_TIMESTAMP WHERE user_id = %s AND chapter_id = %s",
                         (user_id, chapter_id))

        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({"message": "History updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5007) 