from http.server import BaseHTTPRequestHandler
import json
import re
import pandas as pd
from datetime import datetime, timedelta
import io
from google_play_scraper import Sort, reviews_all

def get_app_id(url):
    """Извлекает ID приложения из URL Google Play Store."""
    match = re.search(r'id=([^&]+)', url)
    if match:
        return match.group(1)
    return None

def scrape_reviews(app_id, count_limit=100, country_code='ru', days_limit=365):
    """Собирает, фильтрует и форматирует отзывы."""
    date_cutoff = datetime.now() - timedelta(days=days_limit)
    
    try:
        result = reviews_all(
            app_id,
            lang='ru',
            country=country_code,
            sort=Sort.NEWEST,
        )
        
        data_list = []
        for review in result:
            review_date = review['at'].replace(tzinfo=None)
            
            if review_date >= date_cutoff:
                if len(data_list) >= count_limit:
                    break 

                data_list.append({
                    'Имя_пользователя': review.get('userName', 'N/A'),
                    'Дата_публикации': review['at'].strftime('%Y-%m-%d %H:%M:%S'),
                    'Рейтинг_звезды': review.get('score', 0),
                    'Заголовок_отзыва': review.get('title', '').strip(),
                    'Текст_отзыва': review.get('content', '').strip(),
                    'Страна_отзыва': country_code,
                })
        
        return pd.DataFrame(data_list)

    except Exception as e:
        print(f"Ошибка при скрейпинге {app_id}: {e}")
        return None

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Неверный формат JSON"}).encode())
            return
        
        if not data or 'url' not in data:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Ожидается поле 'url'"}).encode())
            return
        
        app_url = data['url']
        app_id = get_app_id(app_url)

        if not app_id:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Не удалось извлечь ID приложения из ссылки"}).encode())
            return

        # Выполняем скрейпинг
        df = scrape_reviews(app_id)

        if df is None:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Не удалось получить отзывы для ID: {app_id}"}).encode())
            return
        
        if df.empty:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Отзывы не найдены по заданным фильтрам"}).encode())
            return

        # Подготовка CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_content = csv_buffer.getvalue()
        
        filename = f"reviews_{app_id}_{datetime.now().strftime('%Y%m%d')}.csv"

        # Отправляем CSV файл
        self.send_response(200)
        self.send_header('Content-type', 'text/csv; charset=utf-8')
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(csv_content.encode('utf-8'))
    
    def do_OPTIONS(self):
        # Обработка preflight запросов для CORS
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def end_headers(self):
        # Добавляем CORS заголовки для всех ответов
        self.send_header('Access-Control-Allow-Origin', '*')
        BaseHTTPRequestHandler.end_headers(self)