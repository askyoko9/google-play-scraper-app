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
    
    # Удаляем возможные пробелы
    url = url.strip()
    
    # Пробуем разные форматы URL
    patterns = [
        r'id=([a-zA-Z0-9\._]+)',
        r'/details\?id=([a-zA-Z0-9\._]+)',
        r'store/apps/details\?id=([a-zA-Z0-9\._]+)',
        r'play.google.com/store/apps/details\?id=([a-zA-Z0-9\._]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            app_id = match.group(1)
            print(f"Найден App ID по шаблону {pattern}: {app_id}")
            return app_id
    
    # Если это уже app_id (например, com.whatsapp)
    if re.match(r'^[a-zA-Z0-9\._]+$', url) and '.' in url:
        print(f"Предполагаем, что это уже App ID: {url}")
        return url
    
    return None

def scrape_reviews(app_id, count_limit=100, country_code='ru', days_limit=365):
    """Собирает, фильтрует и форматирует отзывы."""
    if not SCRAPER_AVAILABLE:
        print("Библиотека google-play-scraper недоступна")
        return None
    
    date_cutoff = datetime.now() - timedelta(days=days_limit)
    print(f"Фильтр по дате: от {date_cutoff}")
    
    try:
        print(f"Запрос отзывов для App ID: {app_id}")
        result = reviews_all(
            app_id,
            lang='ru',
            country=country_code,
            sort=Sort.NEWEST,
        )
        
        print(f"Получено отзывов всего: {len(result)}")
        
        data_list = []
        for i, review in enumerate(result):
            try:
                # Преобразуем дату и убираем временную зону
                if 'at' in review and review['at']:
                    review_date = review['at'].replace(tzinfo=None)
                    
                    if review_date >= date_cutoff:
                        if len(data_list) >= count_limit:
                            print(f"Достигнут лимит в {count_limit} отзывов")
                            break
                        
                        data_list.append({
                            'Имя_пользователя': review.get('userName', 'N/A'),
                            'Дата_публикации': review['at'].strftime('%Y-%m-%d %H:%M:%S'),
                            'Рейтинг_звезды': review.get('score', 0),
                            'Заголовок_отзыва': review.get('title', '').strip(),
                            'Текст_отзыва': review.get('content', '').strip(),
                            'Страна_отзыва': country_code,
                        })
                        
                        if i % 20 == 0:
                            print(f"Обработано {i+1} отзывов, отфильтровано {len(data_list)}")
                else:
                    print(f"Отзыв {i} без даты, пропускаем")
                    
            except Exception as e:
                print(f"Ошибка обработки отзыва {i}: {e}")
                continue
        
        print(f"Итого отфильтровано отзывов: {len(data_list)}")
        return data_list

    except Exception as e:
        print(f"Критическая ошибка при скрейпинге {app_id}: {e}")
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
    
    writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    
    for i, row in enumerate(data_list):
        try:
            # Очищаем данные от специальных символов
            cleaned_row = {}
            for key, value in row.items():
                if isinstance(value, str):
                    # Удаляем не-ASCII символы, которые могут сломать CSV
                    cleaned_value = value.encode('utf-8', 'ignore').decode('utf-8')
                    cleaned_row[key] = cleaned_value
                else:
                    cleaned_row[key] = value
            
            writer.writerow(cleaned_row)
            
            if i % 20 == 0:
                print(f"Записано в CSV: {i+1} строк")
                
        except Exception as e:
            print(f"Ошибка записи строки {i} в CSV: {e}")
            continue
    
    csv_content = output.getvalue()
    print(f"Размер CSV: {len(csv_content)} байт")
    return csv_content

def handler(request, response):
    """Основная функция-обработчик для Vercel Serverless."""
    try:
        print("=" * 60)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] НОВЫЙ ЗАПРОС")
        
        # Устанавливаем CORS заголовки
        response.headers.update({
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Accept',
            'Cache-Control': 'no-cache, no-store, must-revalidate'
        })
        
        # Обработка preflight запросов OPTIONS
        if request.method == 'OPTIONS':
            response.status_code = 200
            return response
        
        # Обработка GET запросов (тестирование)
        if request.method == 'GET':
            response.status_code = 200
            response.headers['Content-Type'] = 'application/json'
            response_data = {
                "status": "ok",
                "service": "Google Play Reviews Scraper",
                "endpoint": "POST /api/",
                "parameters": {
                    "url": "URL приложения из Google Play Store"
                },
                "example": {
                    "url": "https://play.google.com/store/apps/details?id=com.whatsapp"
                },
                "filters": "Последние 100 отзывов из РФ за последний год"
            }
            response.body = json.dumps(response_data, indent=2)
            return response
        
        # Обработка POST запросов
        if request.method == 'POST':
            if not request.body:
                response.status_code = 400
                response.headers['Content-Type'] = 'application/json'
                response.body = json.dumps({"error": "Пустое тело запроса"})
                return response
            
            # Читаем и парсим JSON
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError as e:
                response.status_code = 400
                response.headers['Content-Type'] = 'application/json'
                response.body = json.dumps({
                    "error": "Неверный формат JSON",
                    "details": str(e)
                })
                return response
            
            if 'url' not in data:
                response.status_code = 400
                response.headers['Content-Type'] = 'application/json'
                response.body = json.dumps({"error": "Ожидается поле 'url' в JSON"})
                return response
            
            app_url = data['url'].strip()
            print(f"Получен URL: {app_url}")
            
            if not app_url:
                response.status_code = 400
                response.headers['Content-Type'] = 'application/json'
                response.body = json.dumps({"error": "URL не может быть пустым"})
                return response
            
            # Извлекаем App ID
            app_id = get_app_id(app_url)
            if not app_id:
                response.status_code = 400
                response.headers['Content-Type'] = 'application/json'
                response.body = json.dumps({
                    "error": "Не удалось извлечь ID приложения",
                    "hint": "Используйте формат: https://play.google.com/store/apps/details?id=com.example.app",
                    "received_url": app_url
                })
                return response
            
            print(f"Извлечен App ID: {app_id}")
            
            if not SCRAPER_AVAILABLE:
                response.status_code = 500
                response.headers['Content-Type'] = 'application/json'
                response.body = json.dumps({"error": "Сервис временно недоступен"})
                return response
            
            # Выполняем скрейпинг
            print(f"Начинаем сбор отзывов для {app_id}...")
            start_time = datetime.now()
            reviews_data = scrape_reviews(app_id)
            elapsed_time = (datetime.now() - start_time).total_seconds()
            print(f"Сбор занял {elapsed_time:.2f} секунд")
            
            if reviews_data is None:
                response.status_code = 500
                response.headers['Content-Type'] = 'application/json'
                response.body = json.dumps({
                    "error": "Не удалось собрать отзывы",
                    "app_id": app_id,
                    "hint": "Проверьте правильность App ID и доступность приложения"
                })
                return response
            
            print(f"Найдено отзывов: {len(reviews_data)}")
            
            if len(reviews_data) == 0:
                response.status_code = 404
                response.headers['Content-Type'] = 'application/json'
                response.body = json.dumps({
                    "error": "Отзывы не найдены",
                    "app_id": app_id,
                    "filters": "РФ, последний год",
                    "hint": "Попробуйте другое приложение или измените фильтры"
                })
                return response
            
            # Создаем CSV
            print("Создаем CSV...")
            csv_data = create_csv_data(reviews_data)
            filename = f"reviews_{app_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            # Отправляем CSV
            response.status_code = 200
            response.headers['Content-Type'] = 'text/csv; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            response.body = csv_data
            
            print(f"Отправляем файл: {filename}")
            print("=" * 60)
            
            return response
    
    except Exception as e:
        print(f"НЕОЖИДАННАЯ ОШИБКА: {e}")
        traceback.print_exc()
        
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        response.body = json.dumps({
            "error": "Внутренняя ошибка сервера",
            "details": str(e)
        })
        return response