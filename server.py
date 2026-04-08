from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
import os
import time
import hashlib
from datetime import datetime
import sys

# Принудительный вывод логов в stderr для Render
print("=" * 60, file=sys.stderr)
print("🚀 STARTING VOLITS SERVER...", file=sys.stderr)
print("=" * 60, file=sys.stderr)

app = Flask(__name__)

# Настройка CORS - разрешаем все для теста
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Accept", "Authorization"]
    }
})

print("✅ CORS configured", file=sys.stderr)

# Хранилища данных
users_db = {}
messages_db = {}
pending_events = {}
friend_requests_db = {}

def init_test_data():
    """Инициализация тестовых данных"""
    print("📦 Initializing test data...", file=sys.stderr)
    
    # Тестовый пользователь
    if 'test' not in users_db:
        users_db['test'] = {
            "login": "test",
            "password": "test123",
            "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=test",
            "registered": datetime.now().strftime("%d.%m.%Y"),
            "friends": [],
            "status": "online"
        }
        pending_events['test'] = []
        friend_requests_db['test'] = []
    
    # Админ пользователь
    if 'admin' not in users_db:
        users_db['admin'] = {
            "login": "admin",
            "password": "admin123",
            "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=admin",
            "registered": datetime.now().strftime("%d.%m.%Y"),
            "friends": [],
            "status": "online"
        }
        pending_events['admin'] = []
        friend_requests_db['admin'] = []
    
    print(f"✅ Test data ready: {len(users_db)} users", file=sys.stderr)

# ==================== СТАТИЧЕСКИЕ МАРШРУТЫ ====================

@app.route('/')
def serve_index():
    print("📍 GET /", file=sys.stderr)
    try:
        return send_from_directory('.', 'index.html')
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 404

@app.route('/login/')
@app.route('/login')
def serve_login():
    print("📍 GET /login/", file=sys.stderr)
    try:
        return send_from_directory('login', 'index.html')
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 404

@app.route('/register/')
@app.route('/register')
def serve_register():
    print("📍 GET /register/", file=sys.stderr)
    try:
        return send_from_directory('register', 'index.html')
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 404

# ==================== API МАРШРУТЫ ====================

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    """Проверка работоспособности API"""
    if request.method == 'OPTIONS':
        return '', 200
    print("📍 GET /api/health", file=sys.stderr)
    return jsonify({
        "status": "ok",
        "users": len(users_db),
        "messages": sum(len(m) for m in messages_db.values()),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/register', methods=['POST', 'OPTIONS'])
def register():
    """Регистрация нового пользователя"""
    if request.method == 'OPTIONS':
        return '', 200
    
    print("📍 POST /api/register", file=sys.stderr)
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No JSON data"}), 400
        
        login = data.get('login', '').strip()
        password = data.get('password', '')
        avatar = data.get('avatar', '')
        
        print(f"📝 Register attempt: {login}", file=sys.stderr)
        
        if not login or not password:
            return jsonify({"status": "error", "message": "Заполните все поля"}), 400
        
        if login in users_db:
            return jsonify({"status": "error", "message": "Пользователь уже существует"}), 409
        
        # Создаем пользователя
        users_db[login] = {
            "login": login,
            "password": password,  # Временно без хеша для отладки
            "avatar": avatar if avatar else f"https://api.dicebear.com/7.x/avataaars/svg?seed={login}",
            "registered": datetime.now().strftime("%d.%m.%Y"),
            "friends": [],
            "status": "online"
        }
        pending_events[login] = []
        friend_requests_db[login] = []
        
        print(f"✅ User registered: {login}", file=sys.stderr)
        return jsonify({
            "status": "ok",
            "message": "Регистрация успешна",
            "user": users_db[login]
        }), 201
        
    except Exception as e:
        print(f"❌ Register error: {str(e)}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    """Вход пользователя"""
    if request.method == 'OPTIONS':
        return '', 200
    
    print("📍 POST /api/login", file=sys.stderr)
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No JSON data"}), 400
        
        login = data.get('login', '').strip()
        password = data.get('password', '')
        
        print(f"📝 Login attempt: {login}", file=sys.stderr)
        
        if login not in users_db:
            return jsonify({"status": "error", "message": "Пользователь не найден"}), 404
        
        user = users_db[login]
        
        # Проверка пароля (для авто-входа пустой пароль пропускаем)
        if password == '' or user['password'] == password:
            user['status'] = 'online'
            user['friends'] = friend_requests_db.get(login, [])
            print(f"✅ Login successful: {login}", file=sys.stderr)
            return jsonify({"status": "ok", "user": user}), 200
        
        return jsonify({"status": "error", "message": "Неверный пароль"}), 401
        
    except Exception as e:
        print(f"❌ Login error: {str(e)}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/logout', methods=['POST', 'OPTIONS'])
def logout():
    """Выход пользователя"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        login = data.get('login', '')
        if login in users_db:
            users_db[login]['status'] = 'offline'
            print(f"👋 Logout: {login}", file=sys.stderr)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error"}), 500

@app.route('/api/search_users', methods=['POST', 'OPTIONS'])
def search_users():
    """Поиск пользователей"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        query = data.get('query', '').lower()
        current_user = data.get('current_user', '')
        
        results = []
        for login, user in users_db.items():
            if login != current_user and query in login.lower():
                results.append({
                    "login": login,
                    "avatar": user.get('avatar', ''),
                    "status": user.get('status', 'offline'),
                    "is_friend": login in friend_requests_db.get(current_user, [])
                })
        
        return jsonify({"users": results})
    except Exception as e:
        return jsonify({"users": []}), 500

@app.route('/api/send_friend_request', methods=['POST', 'OPTIONS'])
def send_friend_request():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        from_user = data.get('from')
        to_user = data.get('to')
        
        if to_user in pending_events:
            pending_events[to_user].append({
                "type": "friend_request",
                "from": from_user,
                "from_avatar": users_db.get(from_user, {}).get('avatar', '')
            })
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error"}), 500

@app.route('/api/accept_friend', methods=['POST', 'OPTIONS'])
def accept_friend():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        user = data.get('user')
        friend = data.get('friend')
        
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
        
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error"}), 500

@app.route('/api/get_messages', methods=['POST', 'OPTIONS'])
def get_messages():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        user = data.get('user')
        with_user = data.get('with')
        chat_key = ':'.join(sorted([user, with_user]))
        return jsonify({"messages": messages_db.get(chat_key, [])})
    except Exception as e:
        return jsonify({"messages": []}), 500

@app.route('/api/send_message', methods=['POST', 'OPTIONS'])
def send_message():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        from_user = data.get('from')
        to_user = data.get('to')
        text = data.get('message')
        
        chat_key = ':'.join(sorted([from_user, to_user]))
        if chat_key not in messages_db:
            messages_db[chat_key] = []
        
        msg = {
            "id": str(int(time.time() * 1000)),
            "from": from_user,
            "to": to_user,
            "text": text,
            "time": datetime.now().strftime("%H:%M")
        }
        messages_db[chat_key].append(msg)
        
        if to_user in pending_events:
            pending_events[to_user].append({
                "type": "new_message",
                "from": from_user,
                "message": text
            })
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error"}), 500

@app.route('/api/poll', methods=['POST', 'OPTIONS'])
def poll():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        user = data.get('user')
        events = pending_events.get(user, [])
        pending_events[user] = []
        return jsonify({"events": events})
    except Exception as e:
        return jsonify({"events": []}), 500

@app.route('/api/update_avatar', methods=['POST', 'OPTIONS'])
def update_avatar():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        user = data.get('user')
        avatar = data.get('avatar')
        if user in users_db:
            users_db[user]['avatar'] = avatar
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error"}), 500

# ==================== ЗАПУСК ====================

# Инициализация
init_test_data()

# Выводим все зарегистрированные маршруты для отладки
print("\n📋 REGISTERED ROUTES:", file=sys.stderr)
for rule in app.url_map.iter_rules():
    print(f"   {rule.methods} {rule.rule}", file=sys.stderr)

print("\n" + "=" * 60, file=sys.stderr)
print("🌎 VOLits Server Ready!", file=sys.stderr)
print("👥 Test users: test/test123, admin/admin123", file=sys.stderr)
print("=" * 60, file=sys.stderr)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🔌 Starting on port {port}...", file=sys.stderr)
    app.run(host='0.0.0.0', port=port, debug=False)
