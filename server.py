from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
import json
import os
import time
import hashlib
from datetime import datetime
from functools import wraps

app = Flask(__name__, static_folder='.')
CORS(app)  # Разрешаем CORS для всех доменов

# ==================== ХРАНИЛИЩА ДАННЫХ ====================

# База данных пользователей: { "username": user_data }
users_db = {}

# Сообщения: { "user1:user2": [список сообщений] }
messages_db = {}

# События для polling: { "username": [список событий] }
pending_events = {}

# Запросы в друзья: { "username": [список запросов] }
friend_requests_db = {}

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def hash_password(password):
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

def init_test_data():
    """Инициализация тестовых данных"""
    # Создаём тестовых пользователей
    if 'admin' not in users_db:
        users_db['admin'] = {
            "login": "admin",
            "password": hash_password("admin123"),
            "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=admin",
            "registered": datetime.now().strftime("%d.%m.%Y"),
            "friends": [],
            "status": "online"
        }
        pending_events['admin'] = []
        friend_requests_db['admin'] = []
    
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
        friend_requests_db['alex'] = []
    
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
        friend_requests_db['maria'] = []

# ==================== МАРШРУТЫ ДЛЯ СТРАНИЦ ====================

@app.route('/')
def serve_index():
    """Главная страница мессенджера"""
    try:
        return send_from_directory('.', 'index.html')
    except Exception as e:
        return jsonify({"error": str(e)}), 404

@app.route('/login/')
def serve_login():
    """Страница входа"""
    try:
        return send_from_directory('login', 'index.html')
    except Exception as e:
        return jsonify({"error": str(e)}), 404

@app.route('/register/')
def serve_register():
    """Страница регистрации"""
    try:
        return send_from_directory('register', 'index.html')
    except Exception as e:
        return jsonify({"error": str(e)}), 404

# ==================== API ЭНДПОИНТЫ ====================

@app.route('/api/register', methods=['POST'])
def register():
    """
    Регистрация нового пользователя
    Ожидает: { login, password, avatar (опционально) }
    Возвращает: { status, message }
    """
    try:
        data = request.json
        login = data.get('login', '').strip()
        password = data.get('password', '')
        avatar = data.get('avatar', '')
        
        # Валидация
        if not login or not password:
            return jsonify({
                "status": "error", 
                "message": "Заполните все поля"
            }), 400
        
        if len(login) < 3:
            return jsonify({
                "status": "error", 
                "message": "Логин должен содержать минимум 3 символа"
            }), 400
        
        if len(password) < 4:
            return jsonify({
                "status": "error", 
                "message": "Пароль должен содержать минимум 4 символа"
            }), 400
        
        # Проверка существования
        if login in users_db:
            return jsonify({
                "status": "error", 
                "message": "Пользователь уже существует"
            }), 409
        
        # Создаём пользователя
        users_db[login] = {
            "login": login,
            "password": hash_password(password),
            "avatar": avatar if avatar else f"https://api.dicebear.com/7.x/avataaars/svg?seed={login}",
            "registered": datetime.now().strftime("%d.%m.%Y"),
            "friends": [],
            "status": "online"
        }
        
        # Инициализируем хранилища для пользователя
        pending_events[login] = []
        friend_requests_db[login] = []
        
        print(f"✅ Новый пользователь: {login}")
        
        return jsonify({
            "status": "ok", 
            "message": "Регистрация успешна"
        }), 201
        
    except Exception as e:
        print(f"❌ Ошибка в /api/register: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": "Внутренняя ошибка сервера"
        }), 500

@app.route('/api/login', methods=['POST'])
def login():
    """
    Вход пользователя
    Ожидает: { login, password }
    Возвращает: { status, user }
    """
    try:
        data = request.json
        login = data.get('login', '').strip()
        password = data.get('password', '')
        
        if not login:
            return jsonify({
                "status": "error", 
                "message": "Укажите логин"
            }), 400
        
        # Проверка пользователя
        if login not in users_db:
            return jsonify({
                "status": "error", 
                "message": "Пользователь не найден"
            }), 404
        
        user = users_db[login]
        
        # Авто-вход по сессии (пустой пароль)
        if password == '':
            user['status'] = 'online'
            # Обновляем список друзей
            user['friends'] = friend_requests_db.get(login, [])
            return jsonify({
                "status": "ok",
                "user": user
            }), 200
        
        # Обычный вход с паролем
        if user['password'] == hash_password(password):
            user['status'] = 'online'
            # Обновляем список друзей
            user['friends'] = friend_requests_db.get(login, [])
            print(f"✅ Вход: {login}")
            return jsonify({
                "status": "ok",
                "user": user
            }), 200
        
        return jsonify({
            "status": "error", 
            "message": "Неверный пароль"
        }), 401
        
    except Exception as e:
        print(f"❌ Ошибка в /api/login: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": "Внутренняя ошибка сервера"
        }), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """
    Выход пользователя
    Ожидает: { login }
    Возвращает: { status }
    """
    try:
        data = request.json
        login = data.get('login', '').strip()
        
        if login in users_db:
            users_db[login]['status'] = 'offline'
            print(f"👋 Выход: {login}")
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        print(f"❌ Ошибка в /api/logout: {str(e)}")
        return jsonify({"status": "error"}), 500

@app.route('/api/search_users', methods=['POST'])
def search_users():
    """
    Поиск пользователей
    Ожидает: { query, current_user }
    Возвращает: { users }
    """
    try:
        data = request.json
        query = data.get('query', '').lower()
        current_user = data.get('current_user', '')
        
        results = []
        for login, user_data in users_db.items():
            # Исключаем себя и проверяем совпадение
            if login != current_user and query in login.lower():
                results.append({
                    "login": login,
                    "avatar": user_data.get('avatar', f"https://api.dicebear.com/7.x/avataaars/svg?seed={login}"),
                    "status": user_data.get('status', 'offline'),
                    "is_friend": login in friend_requests_db.get(current_user, [])
                })
        
        # Ограничиваем количество результатов
        results = results[:20]
        
        return jsonify({"users": results}), 200
        
    except Exception as e:
        print(f"❌ Ошибка в /api/search_users: {str(e)}")
        return jsonify({"users": []}), 500

@app.route('/api/send_friend_request', methods=['POST'])
def send_friend_request():
    """
    Отправка запроса в друзья
    Ожидает: { from, to }
    Возвращает: { status }
    """
    try:
        data = request.json
        from_user = data.get('from', '').strip()
        to_user = data.get('to', '').strip()
        
        if from_user not in users_db or to_user not in users_db:
            return jsonify({"status": "error", "message": "Пользователь не найден"}), 404
        
        # Проверяем, не друзья ли уже
        if to_user in friend_requests_db.get(from_user, []):
            return jsonify({"status": "error", "message": "Уже друзья"}), 400
        
        # Создаём событие для получателя
        event = {
            "type": "friend_request",
            "from": from_user,
            "from_avatar": users_db[from_user].get('avatar', f"https://api.dicebear.com/7.x/avataaars/svg?seed={from_user}")
        }
        
        if to_user in pending_events:
            pending_events[to_user].append(event)
        
        print(f"📨 Запрос в друзья: {from_user} -> {to_user}")
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        print(f"❌ Ошибка в /api/send_friend_request: {str(e)}")
        return jsonify({"status": "error"}), 500

@app.route('/api/accept_friend', methods=['POST'])
def accept_friend():
    """
    Принятие запроса в друзья
    Ожидает: { user, friend }
    Возвращает: { status }
    """
    try:
        data = request.json
        user = data.get('user', '').strip()
        friend = data.get('friend', '').strip()
        
        if user not in users_db or friend not in users_db:
            return jsonify({"status": "error", "message": "Пользователь не найден"}), 404
        
        # Добавляем друг другу в друзья
        if user not in friend_requests_db:
            friend_requests_db[user] = []
        if friend not in friend_requests_db:
            friend_requests_db[friend] = []
        
        if friend not in friend_requests_db[user]:
            friend_requests_db[user].append(friend)
        if user not in friend_requests_db[friend]:
            friend_requests_db[friend].append(user)
        
        # Обновляем в users_db
        users_db[user]['friends'] = friend_requests_db[user]
        users_db[friend]['friends'] = friend_requests_db[friend]
        
        # Уведомляем отправителя
        event = {
            "type": "friend_accepted",
            "from": user
        }
        
        if friend in pending_events:
            pending_events[friend].append(event)
        
        print(f"✅ Дружба принята: {user} и {friend} теперь друзья")
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        print(f"❌ Ошибка в /api/accept_friend: {str(e)}")
        return jsonify({"status": "error"}), 500

@app.route('/api/get_messages', methods=['POST'])
def get_messages():
    """
    Получение истории сообщений
    Ожидает: { user, with }
    Возвращает: { messages }
    """
    try:
        data = request.json
        user = data.get('user', '').strip()
        with_user = data.get('with', '').strip()
        
        # Сортируем имена для создания ключа чата
        chat_key = ':'.join(sorted([user, with_user]))
        
        if chat_key not in messages_db:
            messages_db[chat_key] = []
        
        return jsonify({"messages": messages_db[chat_key]}), 200
        
    except Exception as e:
        print(f"❌ Ошибка в /api/get_messages: {str(e)}")
        return jsonify({"messages": []}), 500

@app.route('/api/send_message', methods=['POST'])
def send_message():
    """
    Отправка сообщения
    Ожидает: { from, to, message }
    Возвращает: { status }
    """
    try:
        data = request.json
        from_user = data.get('from', '').strip()
        to_user = data.get('to', '').strip()
        message_text = data.get('message', '').strip()
        
        if not message_text:
            return jsonify({"status": "error", "message": "Сообщение не может быть пустым"}), 400
        
        # Создаём ключ чата
        chat_key = ':'.join(sorted([from_user, to_user]))
        
        if chat_key not in messages_db:
            messages_db[chat_key] = []
        
        # Создаём сообщение
        message = {
            "id": str(int(time.time() * 1000)),
            "from": from_user,
            "to": to_user,
            "text": message_text,
            "time": datetime.now().strftime("%H:%M"),
            "timestamp": time.time()
        }
        
        messages_db[chat_key].append(message)
        
        # Добавляем событие для получателя
        event = {
            "type": "new_message",
            "from": from_user,
            "message": message_text
        }
        
        if to_user in pending_events:
            pending_events[to_user].append(event)
        
        print(f"💬 Сообщение от {from_user} к {to_user}: {message_text[:50]}")
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        print(f"❌ Ошибка в /api/send_message: {str(e)}")
        return jsonify({"status": "error"}), 500

@app.route('/api/poll', methods=['POST'])
def poll():
    """
    Polling для real-time обновлений
    Ожидает: { user }
    Возвращает: { events }
    """
    try:
        data = request.json
        user = data.get('user', '').strip()
        
        # Получаем события для пользователя
        events = pending_events.get(user, [])
        
        # Очищаем события после отправки
        if user in pending_events:
            pending_events[user] = []
        
        return jsonify({"events": events}), 200
        
    except Exception as e:
        print(f"❌ Ошибка в /api/poll: {str(e)}")
        return jsonify({"events": []}), 500

@app.route('/api/update_avatar', methods=['POST'])
def update_avatar():
    """
    Обновление аватара пользователя
    Ожидает: { user, avatar }
    Возвращает: { status }
    """
    try:
        data = request.json
        user = data.get('user', '').strip()
        avatar = data.get('avatar', '')
        
        if user not in users_db:
            return jsonify({"status": "error", "message": "Пользователь не найден"}), 404
        
        # Обновляем аватар
        users_db[user]['avatar'] = avatar
        
        # Уведомляем друзей об обновлении аватара
        for friend in friend_requests_db.get(user, []):
            event = {
                "type": "avatar_updated",
                "user": user,
                "avatar": avatar
            }
            if friend in pending_events:
                pending_events[friend].append(event)
        
        print(f"🖼️ Аватар обновлён для {user}")
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        print(f"❌ Ошибка в /api/update_avatar: {str(e)}")
        return jsonify({"status": "error"}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Проверка работоспособности сервера
    Возвращает: { status, users_count }
    """
    return jsonify({
        "status": "ok",
        "users_count": len(users_db),
        "messages_count": sum(len(msgs) for msgs in messages_db.values()),
        "timestamp": datetime.now().isoformat()
    }), 200

# ==================== ЗАПУСК СЕРВЕРА ====================

if __name__ == '__main__':
    # Инициализируем тестовые данные
    init_test_data()
    
    print("=" * 60)
    print("🌎 VOLits Messenger Server v2.0")
    print("=" * 60)
    print(f"📡 Сервер запущен: http://localhost:5000")
    print(f"👥 Тестовые аккаунты:")
    for login, user_data in users_db.items():
        print(f"   • {login} / пароль: {login if login == 'admin' else '123456'}")
    print("=" * 60)
    print("💡 Доступные страницы:")
    print(f"   • Главная: http://localhost:5000/")
    print(f"   • Вход: http://localhost:5000/login/")
    print(f"   • Регистрация: http://localhost:5000/register/")
    print("=" * 60)
    
    # Запускаем сервер
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        threaded=True
    )
