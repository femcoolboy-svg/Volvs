from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
import os
import time
from datetime import datetime
import hashlib

app = Flask(__name__, static_folder='.')
CORS(app)

# База данных в памяти
users_db = {
    "admin": {
        "password": hashlib.sha256("admin123".encode()).hexdigest(),
        "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=admin",
        "status": "online",
        "registered": "2024-01-15",
        "friends": []
    }
}

# Хранилища для real-time
pending_events = {}
messages_db = {}
friend_requests = {}

# Инициализация структур
for user in users_db:
    pending_events[user] = []
    messages_db[user] = {}
    friend_requests[user] = []

# Маршруты для статических файлов
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/login/')
def serve_login():
    return send_from_directory('login', 'index.html')

@app.route('/register/')
def serve_register():
    return send_from_directory('register', 'index.html')

# API эндпоинты
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    login = data.get('login', '').strip()
    password = data.get('password', '').strip()
    avatar = data.get('avatar', '')
    
    if not login or not password:
        return jsonify({'status': 'error', 'message': 'Заполните все поля'}), 400
    
    if login in users_db:
        return jsonify({'status': 'error', 'message': 'Пользователь уже существует'}), 409
    
    if not avatar:
        avatar = f"https://api.dicebear.com/7.x/avataaars/svg?seed={login}"
    
    users_db[login] = {
        'password': hashlib.sha256(password.encode()).hexdigest(),
        'avatar': avatar,
        'status': 'online',
        'registered': datetime.now().strftime('%Y-%m-%d'),
        'friends': []
    }
    pending_events[login] = []
    messages_db[login] = {}
    friend_requests[login] = []
    
    return jsonify({'status': 'ok', 'message': 'Регистрация успешна!'}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    login = data.get('login', '').strip()
    password = data.get('password', '').strip()
    
    user = users_db.get(login)
    if not user or user['password'] != hashlib.sha256(password.encode()).hexdigest():
        return jsonify({'status': 'error', 'message': 'Неверный логин или пароль'}), 401
    
    user['status'] = 'online'
    
    return jsonify({
        'status': 'ok',
        'user': {
            'login': login,
            'avatar': user['avatar'],
            'status': user['status'],
            'friends': user['friends'],
            'registered': user['registered']
        }
    }), 200

@app.route('/api/logout', methods=['POST'])
def logout():
    data = request.json
    login = data.get('login', '').strip()
    
    if login in users_db:
        users_db[login]['status'] = 'offline'
    
    return jsonify({'status': 'ok'})

@app.route('/api/poll', methods=['POST'])
def poll():
    data = request.json
    user = data.get('user')
    
    if user not in pending_events:
        return jsonify({'events': [], 'timestamp': time.time()})
    
    events = pending_events[user].copy()
    pending_events[user] = []
    
    return jsonify({'events': events, 'timestamp': time.time()})

@app.route('/api/send_message', methods=['POST'])
def send_message():
    data = request.json
    from_user = data.get('from')
    to_user = data.get('to')
    message = data.get('message')
    
    if to_user not in messages_db:
        messages_db[to_user] = {}
    if from_user not in messages_db[to_user]:
        messages_db[to_user][from_user] = []
    
    msg_obj = {
        'id': int(time.time()),
        'from': from_user,
        'text': message,
        'time': datetime.now().strftime('%H:%M'),
        'timestamp': time.time()
    }
    
    messages_db[to_user][from_user].append(msg_obj)
    
    event = {
        'type': 'new_message',
        'from': from_user,
        'message': msg_obj
    }
    
    if to_user in pending_events:
        pending_events[to_user].append(event)
    
    return jsonify({'status': 'ok'})

@app.route('/api/get_messages', methods=['POST'])
def get_messages():
    data = request.json
    user = data.get('user')
    with_user = data.get('with')
    
    if user not in messages_db or with_user not in messages_db[user]:
        return jsonify({'messages': []})
    
    return jsonify({'messages': messages_db[user][with_user]})

@app.route('/api/send_friend_request', methods=['POST'])
def send_friend_request():
    data = request.json
    from_user = data.get('from')
    to_user = data.get('to')
    
    if to_user in users_db[from_user]['friends']:
        return jsonify({'status': 'error', 'message': 'Уже друзья'}), 400
    
    event = {
        'type': 'friend_request',
        'from': from_user,
        'from_avatar': users_db[from_user]['avatar']
    }
    
    if to_user in pending_events:
        pending_events[to_user].append(event)
    
    friend_requests[to_user].append({'from': from_user, 'status': 'pending'})
    
    return jsonify({'status': 'ok'})

@app.route('/api/accept_friend', methods=['POST'])
def accept_friend():
    data = request.json
    user = data.get('user')
    friend = data.get('friend')
    
    if friend not in users_db[user]['friends']:
        users_db[user]['friends'].append(friend)
    if user not in users_db[friend]['friends']:
        users_db[friend]['friends'].append(user)
    
    friend_requests[user] = [req for req in friend_requests[user] if req['from'] != friend]
    
    event = {'type': 'friend_accepted', 'from': user}
    if friend in pending_events:
        pending_events[friend].append(event)
    
    return jsonify({'status': 'ok'})

@app.route('/api/search_users', methods=['POST'])
def search_users():
    data = request.json
    query = data.get('query', '').lower()
    current_user = data.get('current_user')
    
    results = []
    for login, user_data in users_db.items():
        if query in login.lower() and login != current_user:
            results.append({
                'login': login,
                'avatar': user_data['avatar'],
                'status': user_data['status'],
                'is_friend': login in users_db[current_user]['friends']
            })
    
    return jsonify({'users': results[:20]})

@app.route('/api/update_avatar', methods=['POST'])
def update_avatar():
    data = request.json
    user = data.get('user')
    avatar = data.get('avatar')
    
    if user in users_db:
        users_db[user]['avatar'] = avatar
        
        for friend in users_db[user]['friends']:
            event = {'type': 'avatar_updated', 'user': user, 'avatar': avatar}
            if friend in pending_events:
                pending_events[friend].append(event)
        
        return jsonify({'status': 'ok'})
    
    return jsonify({'status': 'error'}), 404

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 VOLits Messenger Server запущен!")
    print("📡 API: http://localhost:5000")
    print("👥 Тестовый пользователь: admin / admin123")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
