from flask import Flask, request, jsonify
from flask_cors import CORS
import re

app = Flask(__name__)
CORS(app, origins=["http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:3000", "*"])

# База данных пользователей (заглушка)
users_db = {
    "admin": {"password": "admin123", "registered": "2024-01-15"},
    "Alice": {"password": "alice123", "registered": "2024-01-20"},
    "Bob": {"password": "bob123", "registered": "2024-01-25"},
    "VOLits_Team": {"password": "team2024", "registered": "2024-01-10"}
}

# Список пользователей для поиска
users_list = ["Alice", "Bob", "Charlie", "David", "Eva", "VOLits_Team", "Frank", "Grace"]

@app.route('/api/register', methods=['POST'])
def register():
    """Регистрация нового пользователя"""
    data = request.get_json()
    login = data.get('login', '').strip()
    password = data.get('password', '').strip()
    
    # Валидация
    if not login or not password:
        return jsonify({
            'status': 'error',
            'message': 'Логин и пароль обязательны'
        }), 400
    
    if len(login) < 3:
        return jsonify({
            'status': 'error',
            'message': 'Логин должен содержать минимум 3 символа'
        }), 400
    
    if len(password) < 4:
        return jsonify({
            'status': 'error',
            'message': 'Пароль должен содержать минимум 4 символа'
        }), 400
    
    # Проверка существования пользователя
    if login in users_db:
        return jsonify({
            'status': 'error',
            'message': 'Пользователь с таким логином уже существует'
        }), 409
    
    # Регистрация нового пользователя
    from datetime import datetime
    users_db[login] = {
        'password': password,
        'registered': datetime.now().strftime('%Y-%m-%d')
    }
    users_list.append(login)
    
    return jsonify({
        'status': 'ok',
        'message': f'Welcome to VOLits, {login}!',
        'user': login
    }), 201

@app.route('/api/login', methods=['POST'])
def login():
    """Авторизация пользователя"""
    data = request.get_json()
    login = data.get('login', '').strip()
    password = data.get('password', '').strip()
    
    if not login or not password:
        return jsonify({
            'status': 'error',
            'message': 'Логин и пароль обязательны'
        }), 400
    
    # Проверка учетных данных
    user = users_db.get(login)
    if not user or user['password'] != password:
        return jsonify({
            'status': 'error',
            'message': 'Неверный логин или пароль'
        }), 401
    
    return jsonify({
        'status': 'ok',
        'message': f'Добро пожаловать, {login}!',
        'token': login,
        'user': login
    }), 200

@app.route('/api/users', methods=['GET'])
def get_users():
    """Получение списка пользователей для поиска"""
    search = request.args.get('search', '').lower()
    if search:
        filtered = [u for u in users_list if search in u.lower()]
        return jsonify({
            'users': filtered[:10]  # Ограничиваем 10 результатами
        })
    return jsonify({
        'users': users_list
    })

@app.route('/api/user/<username>', methods=['GET'])
def get_user_info(username):
    """Получение информации о пользователе"""
    user = users_db.get(username)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'username': username,
        'registered': user['registered'],
        'status': 'online'  # Заглушка
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности API"""
    return jsonify({
        'status': 'ok',
        'message': 'VOLits API is running',
        'users_count': len(users_db)
    })

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 VOLits Messenger Server Starting...")
    print("📡 API доступен по адресу: http://localhost:5000")
    print("👥 Тестовые пользователи:")
    for user in users_db:
        print(f"   - {user} / {users_db[user]['password']}")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
