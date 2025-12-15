from http.server import BaseHTTPRequestHandler
import json
import re
import pandas as pd
from datetime import datetime, timedelta
import io
import sys
import traceback

# Импортируем google-play-scraper с обработкой ошибок импорта
try:
    from google_play_scraper import Sort, reviews_all
    SCRAPER_AVAILABLE = True
except ImportError as e:
    SCRAPER_AVAILABLE = False
    print(f"Ошибка импорта google-play-scraper: {e}")

def get_app_id(url):
    """Извлекает ID приложения из URL Google Play Store."""
    if not url:
        return None
    match = re.search(r'id=([^&]+)', url)
    if match:
        return match.group(1)
    return None

def scrape_reviews(app_id, count_limit=100, country_code='ru', days_limit=365):
    """Собирает, фильтрует и форматирует отзывы."""
    if not SCRAPER_AVAILABLE:
        return None
    
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
        traceback.print_exc()
        return None

class handler(BaseHTTPRequestHandler):
    def _send_json_response(self, status_code, data):
        """Отправляет JSON ответ."""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def _send_csv_response(self, df, filename):
        """Отправляет CSV файл."""
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_content = csv_buffer.getvalue()
        
        self.send_response(200)
        self.send_header('Content-type', 'text/csv; charset=utf-8')
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(csv_content.encode('utf-8'))
    
    def do_POST(self):
        try:
            # Логируем начало обработки
            print("Начало обработки POST запроса")
            
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                return self._send_json_response(400, {"error": "Пустое тело запроса"})
            
            post_data = self.rfile.read(content_length)
            print(f"Получены данные: {post_data[:100]}...")
            
            try:
                data = json.loads(post_data)
            except json.JSONDecodeError as e:
                print(f"Ошибка декодирования JSON: {e}")
                return self._send_json_response(400, {"error": "Неверный формат JSON"})
            
            if not data or 'url' not in data:
                return self._send_json_response(400, {"error": "Ожидается поле 'url' в JSON"})
            
            app_url = data['url'].strip()
            print(f"URL приложения: {app_url}")
            
            app_id = get_app_id(app_url)
            print(f"Извлеченный App ID: {app_id}")

            if not app_id:
                return self._send_json_response(400, {"error": "Не удалось извлечь ID приложения. Проверьте формат ссылки"})
            
            if not SCRAPER_AVAILABLE:
                return self._send_json_response(500, {"error": "Библиотека google-play-scraper недоступна"})

            # Выполняем скрейпинг
            print(f"Начинаем сбор отзывов для {app_id}...")
            df = scrape_reviews(app_id)
            print(f"Сбор завершен. Размер DataFrame: {len(df) if df is not None else 'None'}")

            if df is None:
                return self._send_json_response(500, {"error": f"Ошибка при сборе отзывов для приложения: {app_id}"})
            
            if df.empty:
                return self._send_json_response(404, {"error": "Отзывы не найдены по заданным фильтрам"})

            # Подготовка и отправка CSV
            filename = f"reviews_{app_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            print(f"Отправка файла: {filename}")
            
            return self._send_csv_response(df, filename)
            
        except Exception as e:
            print(f"Неожиданная ошибка в обработчике: {e}")
            traceback.print_exc()
            return self._send_json_response(500, {"error": f"Внутренняя ошибка сервера: {str(e)}"})
    
    def do_OPTIONS(self):
        """Обработка preflight запросов CORS."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Отключаем стандартное логирование для чистоты вывода."""
        pass