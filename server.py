from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
import os
import time
import hashlib
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)  # Разрешаем всё для простоты

# ============================================
# ДАННЫЕ (просто и понятно)
# ============================================
users = {}  # { "login": { "password": "...", "avatar": "...", "friends": [] } }
messages = {}  # { "user1:user2": [messages] }
events = {}  # { "user": [events] }

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================
def hash_pass(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

# ============================================
# СТАТИЧЕСКИЕ МАРШРУТЫ (HTML СТРАНИЦЫ)
# ============================================
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/login/')
@app.route('/login')
def login_page():
    return send_from_directory('login', 'index.html')

@app.route('/register/')
@app.route('/register')
def register_page():
    return send_from_directory('register', 'index.html')

# ============================================
# API МАРШРУТЫ
# ============================================
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "users": len(users)})

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    login = data.get('login', '').strip()
    password = data.get('password', '')
    avatar = data.get('avatar', '')
    
    if not login or not password:
        return jsonify({"status": "error", "message": "Заполните все поля"})
    
    if login in users:
        return jsonify({"status": "error", "message": "Пользователь уже существует"})
    
    users[login] = {
        "login": login,
        "password": password,
        "avatar": avatar if avatar else f"https://api.dicebear.com/7.x/avataaars/svg?seed={login}",
        "friends": [],
        "status": "online"
    }
    events[login] = []
    
    print(f"✅ Регистрация: {login}")
    return jsonify({"status": "ok", "message": "Регистрация успешна"})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    login = data.get('login', '').strip()
    password = data.get('password', '')
    
    if login not in users:
        return jsonify({"status": "error", "message": "Пользователь не найден"})
    
    user = users[login]
    
    if password == '' or user['password'] == password:
        user['status'] = 'online'
        print(f"✅ Вход: {login}")
        return jsonify({"status": "ok", "user": user})
    
    return jsonify({"status": "error", "message": "Неверный пароль"})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    data = request.json
    login = data.get('login', '')
    if login in users:
        users[login]['status'] = 'offline'
    return jsonify({"status": "ok"})

@app.route('/api/search_users', methods=['POST'])
def api_search_users():
    data = request.json
    query = data.get('query', '').lower()
    current_user = data.get('current_user', '')
    
    results = []
    for login, user in users.items():
        if login != current_user and query in login.lower():
            results.append({
                "login": login,
                "avatar": user['avatar'],
                "status": user['status'],
                "is_friend": login in users[current_user]['friends']
            })
    
    return jsonify({"users": results})

@app.route('/api/send_friend_request', methods=['POST'])
def api_send_friend_request():
    data = request.json
    from_user = data.get('from')
    to_user = data.get('to')
    
    if to_user in events:
        events[to_user].append({
            "type": "friend_request",
            "from": from_user,
            "from_avatar": users[from_user]['avatar']
        })
    
    return jsonify({"status": "ok"})

@app.route('/api/accept_friend', methods=['POST'])
def api_accept_friend():
    data = request.json
    user = data.get('user')
    friend = data.get('friend')
    
    if friend not in users[user]['friends']:
        users[user]['friends'].append(friend)
    if user not in users[friend]['friends']:
        users[friend]['friends'].append(user)
    
    if friend in events:
        events[friend].append({
            "type": "friend_accepted",
            "from": user
        })
    
    return jsonify({"status": "ok"})

@app.route('/api/get_messages', methods=['POST'])
def api_get_messages():
    data = request.json
    user = data.get('user')
    with_user = data.get('with')
    
    key = ':'.join(sorted([user, with_user]))
    msgs = messages.get(key, [])
    
    return jsonify({"messages": msgs})

@app.route('/api/send_message', methods=['POST'])
def api_send_message():
    data = request.json
    from_user = data.get('from')
    to_user = data.get('to')
    text = data.get('message')
    
    key = ':'.join(sorted([from_user, to_user]))
    if key not in messages:
        messages[key] = []
    
    msg = {
        "id": str(int(time.time() * 1000)),
        "from": from_user,
        "to": to_user,
        "text": text,
        "time": datetime.now().strftime("%H:%M")
    }
    messages[key].append(msg)
    
    if to_user in events:
        events[to_user].append({
            "type": "new_message",
            "from": from_user,
            "message": text
        })
    
    return jsonify({"status": "ok"})

@app.route('/api/poll', methods=['POST'])
def api_poll():
    data = request.json
    user = data.get('user')
    
    evts = events.get(user, [])
    events[user] = []
    
    return jsonify({"events": evts})

@app.route('/api/update_avatar', methods=['POST'])
def api_update_avatar():
    data = request.json
    user = data.get('user')
    avatar = data.get('avatar')
    
    if user in users:
        users[user]['avatar'] = avatar
    
    return jsonify({"status": "ok"})

# ============================================
# ЗАПУСК
# ============================================
if __name__ == '__main__':
    # Создаём тестовых пользователей
    users['admin'] = {
        "login": "admin",
        "password": "admin123",
        "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=admin",
        "friends": [],
        "status": "offline"
    }
    users['alex'] = {
        "login": "alex",
        "password": "123456",
        "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=alex",
        "friends": ['admin'],
        "status": "offline"
    }
    users['maria'] = {
        "login": "maria",
        "password": "123456",
        "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=maria",
        "friends": ['admin'],
        "status": "offline"
    }
    
    events['admin'] = []
    events['alex'] = []
    events['maria'] = []
    
    print("=" * 50)
    print("🚀 VOLits SERVER RUNNING")
    print("=" * 50)
    print("📡 API: http://localhost:5000")
    print("👥 Test users:")
    print("   admin / admin123")
    print("   alex / 123456")
    print("   maria / 123456")
    print("=" * 50)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
