# server.py
from flask import Flask, send_from_directory
import sys
import os

# Добавляем путь к api папке
sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))

app = Flask(__name__, static_folder='.', static_url_path='')

# Импортируем API маршруты из api/index.py
from api.index import app as api_app

# Подключаем API маршруты
app.register_blueprint(api_app, url_prefix='/api')

# Главная страница - отдаем index.html
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# Если запрашивают напрямую api/index
@app.route('/api/index')
def api_redirect():
    from flask import request
    from api.index import handle_scrape
    return handle_scrape()

# Обработка статических файлов
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    app.run(debug=True)