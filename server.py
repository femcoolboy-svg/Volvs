# В САМОМ НАЧАЛЕ ФАЙЛА, ПЕРВАЯ СТРОКА:
import sys
print("=" * 50, file=sys.stderr)
print("🚀 SERVER.PY STARTING...", file=sys.stderr)
print("=" * 50, file=sys.stderr)

from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
import json
import os
import time
import hashlib
from datetime import datetime
from functools import wraps

print("✅ Imports loaded", file=sys.stderr)

app = Flask(__name__, static_folder='.')

# РАСШИРЕННЫЕ НАСТРОЙКИ CORS для Render
print("🔧 Configuring CORS...", file=sys.stderr)
CORS(app, 
     origins=[
         'https://volvs.onrender.com',
         'http://localhost:5000',
         'http://localhost:5500',
         'http://127.0.0.1:5000',
         'https://volvs.onrender.com:5000'
     ],
     supports_credentials=True,
     allow_headers=['Content-Type', 'Accept', 'Authorization', 'X-Requested-With'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD'],
     expose_headers=['Content-Type', 'Authorization'])

print("✅ CORS configured", file=sys.stderr)

# Хранилища данных
users_db = {}
messages_db = {}
pending_events = {}
friend_requests_db = {}

def hash_password(password):
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

def init_test_data():
    """Инициализация тестовых данных"""
    print("📦 Initializing test data...", file=sys.stderr)
    
    if 'admin' not in users_db:
        users_db['admin'] = {
            "login": "admin",
            "password": hash_password("admin123"),
            "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=admin",
            "registered": datetime.now().strftime("%d.%m.%Y"),
            "friends": ["alex", "maria"],
            "status": "online"
        }
        pending_events['admin'] = []
        friend_requests_db['admin'] = ['alex', 'maria']
    
    if 'alex' not in users_db:
        users_db['alex'] = {
            "login": "alex",
            "password": hash_password("123456"),
            "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=alex",
            "registered": datetime.now().strftime("%d.%m.%Y"),
            "friends": ["admin"],
            "status": "online"
        }
        pending_events['alex'] = []
        friend_requests_db['alex'] = ['admin']
    
    if 'maria' not in users_db:
        users_db['maria'] = {
            "login": "maria",
            "password": hash_password("123456"),
            "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=maria",
            "registered": datetime.now().strftime("%d.%m.%Y"),
            "friends": ["admin"],
            "status": "offline"
        }
        pending_events['maria'] = []
        friend_requests_db['maria'] = ['admin']
    
    print(f"✅ Test data initialized: {len(users_db)} users", file=sys.stderr)

# Маршруты для статических файлов
@app.route('/')
def serve_index():
    print("📍 GET /", file=sys.stderr)
    try:
        return send_from_directory('.', 'index.html')
    except Exception as e:
        print(f"❌ Error serving /: {str(e)}", file=sys.stderr)
        return jsonify({"error": str(e)}), 404

@app.route('/login/')
@app.route('/login')
def serve_login():
    print("📍 GET /login/", file=sys.stderr)
    try:
        return send_from_directory('login', 'index.html')
    except Exception as e:
        print(f"❌ Error serving /login/: {str(e)}", file=sys.stderr)
        return jsonify({"error": str(e)}), 404

@app.route('/register/')
@app.route('/register')
def serve_register():
    print("📍 GET /register/", file=sys.stderr)
    try:
        return send_from_directory('register', 'index.html')
    except Exception as e:
        print(f"❌ Error serving /register/: {str(e)}", file=sys.stderr)
        return jsonify({"error": str(e)}), 404

# API эндпоинты
@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    print("📍 GET /api/health", file=sys.stderr)
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({
        "status": "ok",
        "users_count": len(users_db),
        "messages_count": sum(len(msgs) for msgs in messages_db.values()),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/register', methods=['POST', 'OPTIONS'])
def register():
    print("📍 POST /api/register", file=sys.stderr)
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        print(f"📝 Register request: {data.get('login')}", file=sys.stderr)
        
        login = data.get('login', '').strip()
        password = data.get('password', '')
        avatar = data.get('avatar', '')
        
        if not login or not password:
            return jsonify({"status": "error", "message": "Заполните все поля"}), 400
        
        if len(login) < 3:
            return jsonify({"status": "error", "message": "Логин должен содержать минимум 3 символа"}), 400
        
        if len(password) < 4:
            return jsonify({"status": "error", "message": "Пароль должен содержать минимум 4 символа"}), 400
        
        if login in users_db:
            return jsonify({"status": "error", "message": "Пользователь уже существует"}), 409
        
        users_db[login] = {
            "login": login,
            "password": hash_password(password),
            "avatar": avatar if avatar else f"https://api.dicebear.com/7.x/avataaars/svg?seed={login}",
            "registered": datetime.now().strftime("%d.%m.%Y"),
            "friends": [],
            "status": "online"
        }
        pending_events[login] = []
        friend_requests_db[login] = []
        
        print(f"✅ New user registered: {login}", file=sys.stderr)
        return jsonify({"status": "ok", "message": "Регистрация успешна"}), 201
    except Exception as e:
        print(f"❌ Register error: {str(e)}", file=sys.stderr)
        return jsonify({"status": "error", "message": "Внутренняя ошибка сервера"}), 500

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    print("📍 POST /api/login", file=sys.stderr)
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        login = data.get('login', '').strip()
        password = data.get('password', '')
        
        print(f"📝 Login request: {login}", file=sys.stderr)
        
        if login not in users_db:
            return jsonify({"status": "error", "message": "Пользователь не найден"}), 404
        
        user = users_db[login]
        
        # Авто-вход по сессии (пустой пароль)
        if password == '':
            user['status'] = 'online'
            user['friends'] = friend_requests_db.get(login, [])
            print(f"✅ Auto-login: {login}", file=sys.stderr)
            return jsonify({"status": "ok", "user": user}), 200
        
        # Обычный вход с паролем
        if user['password'] == hash_password(password):
            user['status'] = 'online'
            user['friends'] = friend_requests_db.get(login, [])
            print(f"✅ Login successful: {login}", file=sys.stderr)
            return jsonify({"status": "ok", "user": user}), 200
        
        print(f"❌ Login failed: {login} - wrong password", file=sys.stderr)
        return jsonify({"status": "error", "message": "Неверный пароль"}), 401
    except Exception as e:
        print(f"❌ Login error: {str(e)}", file=sys.stderr)
        return jsonify({"status": "error", "message": "Внутренняя ошибка"}), 500

@app.route('/api/logout', methods=['POST', 'OPTIONS'])
def logout():
    print("📍 POST /api/logout", file=sys.stderr)
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        login = data.get('login', '').strip()
        if login in users_db:
            users_db[login]['status'] = 'offline'
            print(f"👋 Logout: {login}", file=sys.stderr)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"❌ Logout error: {str(e)}", file=sys.stderr)
        return jsonify({"status": "error"}), 500

@app.route('/api/search_users', methods=['POST', 'OPTIONS'])
def search_users():
    print("📍 POST /api/search_users", file=sys.stderr)
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        query = data.get('query', '').lower()
        current_user = data.get('current_user', '')
        
        print(f"🔍 Search users: query='{query}', current='{current_user}'", file=sys.stderr)
        
        results = []
        for login, user_data in users_db.items():
            if login != current_user and query in login.lower():
                results.append({
                    "login": login,
                    "avatar": user_data.get('avatar', f"https://api.dicebear.com/7.x/avataaars/svg?seed={login}"),
                    "status": user_data.get('status', 'offline'),
                    "is_friend": login in friend_requests_db.get(current_user, [])
                })
        
        print(f"✅ Found {len(results)} users", file=sys.stderr)
        return jsonify({"users": results[:20]}), 200
    except Exception as e:
        print(f"❌ Search users error: {str(e)}", file=sys.stderr)
        return jsonify({"users": []}), 500

@app.route('/api/send_friend_request', methods=['POST', 'OPTIONS'])
def send_friend_request():
    print("📍 POST /api/send_friend_request", file=sys.stderr)
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        from_user = data.get('from', '').strip()
        to_user = data.get('to', '').strip()
        
        print(f"📨 Friend request: {from_user} -> {to_user}", file=sys.stderr)
        
        event = {
            "type": "friend_request",
            "from": from_user,
            "from_avatar": users_db[from_user].get('avatar', '')
        }
        
        if to_user in pending_events:
            pending_events[to_user].append(event)
        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"❌ Send friend request error: {str(e)}", file=sys.stderr)
        return jsonify({"status": "error"}), 500

@app.route('/api/accept_friend', methods=['POST', 'OPTIONS'])
def accept_friend():
    print("📍 POST /api/accept_friend", file=sys.stderr)
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        user = data.get('user', '').strip()
        friend = data.get('friend', '').strip()
        
        print(f"✅ Accept friend: {user} <-> {friend}", file=sys.stderr)
        
        if user not in friend_requests_db:
            friend_requests_db[user] = []
        if friend not in friend_requests_db:
            friend_requests_db[friend] = []
        
        if friend not in friend_requests_db[user]:
            friend_requests_db[user].append(friend)
        if user not in friend_requests_db[friend]:
            friend_requests_db[friend].append(user)
        
        users_db[user]['friends'] = friend_requests_db[user]
        users_db[friend]['friends'] = friend_requests_db[friend]
        
        if friend in pending_events:
            pending_events[friend].append({"type": "friend_accepted", "from": user})
        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"❌ Accept friend error: {str(e)}", file=sys.stderr)
        return jsonify({"status": "error"}), 500

@app.route('/api/get_messages', methods=['POST', 'OPTIONS'])
def get_messages():
    print("📍 POST /api/get_messages", file=sys.stderr)
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        user = data.get('user', '').strip()
        with_user = data.get('with', '').strip()
        
        chat_key = ':'.join(sorted([user, with_user]))
        
        if chat_key not in messages_db:
            messages_db[chat_key] = []
        
        print(f"💬 Get messages: {chat_key} ({len(messages_db[chat_key])} messages)", file=sys.stderr)
        return jsonify({"messages": messages_db[chat_key]}), 200
    except Exception as e:
        print(f"❌ Get messages error: {str(e)}", file=sys.stderr)
        return jsonify({"messages": []}), 500

@app.route('/api/send_message', methods=['POST', 'OPTIONS'])
def send_message():
    print("📍 POST /api/send_message", file=sys.stderr)
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        from_user = data.get('from', '').strip()
        to_user = data.get('to', '').strip()
        message_text = data.get('message', '').strip()
        
        print(f"💬 Send message: {from_user} -> {to_user}: {message_text[:50]}", file=sys.stderr)
        
        chat_key = ':'.join(sorted([from_user, to_user]))
        
        if chat_key not in messages_db:
            messages_db[chat_key] = []
        
        message = {
            "id": str(int(time.time() * 1000)),
            "from": from_user,
            "to": to_user,
            "text": message_text,
            "time": datetime.now().strftime("%H:%M"),
            "timestamp": time.time()
        }
        
        messages_db[chat_key].append(message)
        
        if to_user in pending_events:
            pending_events[to_user].append({
                "type": "new_message",
                "from": from_user,
                "message": message_text
            })
        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"❌ Send message error: {str(e)}", file=sys.stderr)
        return jsonify({"status": "error"}), 500

@app.route('/api/poll', methods=['POST', 'OPTIONS'])
def poll():
    print("📍 POST /api/poll", file=sys.stderr)
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        user = data.get('user', '').strip()
        
        events = pending_events.get(user, [])
        pending_events[user] = []
        
        if events:
            print(f"📡 Poll for {user}: {len(events)} events", file=sys.stderr)
        
        return jsonify({"events": events}), 200
    except Exception as e:
        print(f"❌ Poll error: {str(e)}", file=sys.stderr)
        return jsonify({"events": []}), 500

@app.route('/api/update_avatar', methods=['POST', 'OPTIONS'])
def update_avatar():
    print("📍 POST /api/update_avatar", file=sys.stderr)
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        user = data.get('user', '').strip()
        avatar = data.get('avatar', '')
        
        if user in users_db:
            users_db[user]['avatar'] = avatar
            print(f"🖼️ Avatar updated for {user}", file=sys.stderr)
        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"❌ Update avatar error: {str(e)}", file=sys.stderr)
        return jsonify({"status": "error"}), 500

# Запуск сервера
if __name__ == '__main__':
    print("=" * 50, file=sys.stderr)
    print("🚀 Starting VOLits Server...", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    
    # Инициализируем тестовые данные
    init_test_data()
    
    # Выводим все зарегистрированные маршруты
    print("\n📋 Registered routes:", file=sys.stderr)
    for rule in app.url_map.iter_rules():
        print(f"   {rule.methods} {rule.rule}", file=sys.stderr)
    
    print("\n👥 Test users:", file=sys.stderr)
    for login, user_data in users_db.items():
        print(f"   • {login} / password: {login if login == 'admin' else '123456'}", file=sys.stderr)
    
    print("\n" + "=" * 50, file=sys.stderr)
    print("🌎 Server is ready!", file=sys.stderr)
    print("📡 API: https://volvs.onrender.com", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    
    # Получаем порт из переменной окружения Render
    port = int(os.environ.get('PORT', 5000))
    print(f"🔌 Starting on port {port}...", file=sys.stderr)
    
    # Запускаем сервер
    app.run(
        debug=False,
        host='0.0.0.0',
        port=port,
        threaded=True
    )
