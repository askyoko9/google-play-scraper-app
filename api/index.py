from http.server import BaseHTTPRequestHandler
import json
import re
from datetime import datetime, timedelta
import csv
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
    
    # Пробуем альтернативный формат
    match = re.search(r'/details\?id=([^&]+)', url)
    if match:
        return match.group(1)
    
    # Если это уже app_id
    if '.' in url or 'com.' in url:
        return url
    
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
            try:
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
            except Exception as e:
                print(f"Ошибка обработки отзыва: {e}")
                continue
        
        return data_list

    except Exception as e:
        print(f"Ошибка при скрейпинге {app_id}: {e}")
        traceback.print_exc()
        return None

def create_csv_data(data_list):
    """Создает CSV данные из списка словарей."""
    if not data_list:
        return ""
    
    output = io.StringIO()
    
    # Определяем заголовки
    fieldnames = ['Имя_пользователя', 'Дата_публикации', 'Рейтинг_звезды', 
                  'Заголовок_отзыва', 'Текст_отзыва', 'Страна_отзыва']
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for row in data_list:
        writer.writerow(row)
    
    return output.getvalue()

class handler(BaseHTTPRequestHandler):
    def _send_json_response(self, status_code, data):
        """Отправляет JSON ответ."""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def _send_csv_response(self, csv_data, filename):
        """Отправляет CSV файл."""
        self.send_response(200)
        self.send_header('Content-type', 'text/csv; charset=utf-8')
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(csv_data.encode('utf-8'))
    
    def do_POST(self):
        try:
            print("=== Начало обработки POST запроса ===")
            
            # Проверяем Content-Type
            content_type = self.headers.get('Content-Type', '')
            print(f"Content-Type: {content_type}")
            
            content_length = int(self.headers.get('Content-Length', 0))
            print(f"Content-Length: {content_length}")
            
            if content_length == 0:
                return self._send_json_response(400, {"error": "Пустое тело запроса"})
            
            post_data = self.rfile.read(content_length)
            print(f"Получены данные (первые 500 символов): {post_data[:500]}")
            
            # Парсим JSON
            try:
                data = json.loads(post_data)
            except json.JSONDecodeError as e:
                print(f"Ошибка декодирования JSON: {e}")
                return self._send_json_response(400, {"error": "Неверный формат JSON"})
            
            if not isinstance(data, dict) or 'url' not in data:
                return self._send_json_response(400, {"error": "Ожидается JSON объект с полем 'url'"})
            
            app_url = data['url'].strip()
            print(f"URL приложения: {app_url}")
            
            if not app_url:
                return self._send_json_response(400, {"error": "URL не может быть пустым"})
            
            app_id = get_app_id(app_url)
            print(f"Извлеченный App ID: {app_id}")

            if not app_id:
                return self._send_json_response(400, {"error": "Не удалось извлечь ID приложения. Используйте формат: https://play.google.com/store/apps/details?id=com.example.app"})
            
            if not SCRAPER_AVAILABLE:
                return self._send_json_response(500, {"error": "Библиотека google-play-scraper недоступна. Проверьте установку."})

            # Выполняем скрейпинг
            print(f"Начинаем сбор отзывов для {app_id}...")
            reviews_data = scrape_reviews(app_id)
            
            if reviews_data is None:
                return self._send_json_response(500, {"error": f"Ошибка при сборе отзывов. Проверьте App ID: {app_id}"})
            
            print(f"Сбор завершен. Найдено отзывов: {len(reviews_data)}")
            
            if len(reviews_data) == 0:
                return self._send_json_response(404, {"error": "Отзывы не найдены по заданным фильтрам (РФ, последний год)"})

            # Создаем CSV
            csv_data = create_csv_data(reviews_data)
            filename = f"reviews_{app_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            print(f"Отправка файла: {filename}, размер: {len(csv_data)} байт")
            
            return self._send_csv_response(csv_data, filename)
            
        except Exception as e:
            print(f"Неожиданная ошибка в обработчике: {e}")
            traceback.print_exc()
            return self._send_json_response(500, {"error": f"Внутренняя ошибка сервера: {str(e)}"})
    
    def do_GET(self):
        """Проверка работоспособности API."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "ok",
            "message": "Google Play Scraper API работает",
            "endpoint": "POST /api/ с JSON {'url': 'play.google.com/...'}"
        }).encode())
    
    def do_OPTIONS(self):
        """Обработка preflight запросов CORS."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Сохраняем логи для отладки."""
        print(f"{self.address_string()} - {format % args}")