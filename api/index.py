import json
import re
import sys
import traceback
from datetime import datetime, timedelta

def handler(event, context):
    print("=" * 60)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] НОВЫЙ ЗАПРОС")
    print(f"Метод: {event.get('httpMethod')}")
    print(f"Путь: {event.get('path')}")
    print(f"Заголовки: {event.get('headers', {})}")
    
    # Базовые заголовки
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    
    # OPTIONS запрос (CORS preflight)
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    # GET запрос - информация о сервисе
    if event.get('httpMethod') == 'GET':
        headers['Content-Type'] = 'application/json; charset=utf-8'
        
        response = {
            "status": "ok",
            "service": "Google Play Reviews Scraper API",
            "version": "1.0",
            "endpoints": {
                "GET /": "Эта информация",
                "POST /": "Сбор отзывов (требуется JSON с полем 'url')"
            },
            "example": {
                "url": "https://play.google.com/store/apps/details?id=com.whatsapp"
            },
            "filters": "Последние 100 отзывов из РФ за последний год",
            "output": "CSV файл"
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response, ensure_ascii=False, indent=2)
        }
    
    # POST запрос - основная логика
    if event.get('httpMethod') == 'POST':
        try:
            # Проверяем тело запроса
            if not event.get('body'):
                return error_response(400, "Пустое тело запроса", headers)
            
            # Парсим JSON
            try:
                data = json.loads(event['body'])
            except json.JSONDecodeError as e:
                return error_response(400, f"Неверный формат JSON: {str(e)}", headers)
            
            # Проверяем наличие URL
            if 'url' not in data:
                return error_response(400, "Отсутствует поле 'url' в JSON", headers)
            
            url = data['url'].strip()
            if not url:
                return error_response(400, "URL не может быть пустым", headers)
            
            print(f"Получен URL: {url}")
            
            # Извлекаем App ID
            app_id = extract_app_id(url)
            if not app_id:
                return error_response(400, 
                    f"Не удалось извлечь ID приложения из URL: {url}\n"
                    f"Пример правильного формата: https://play.google.com/store/apps/details?id=com.example.app",
                    headers
                )
            
            print(f"Извлечен App ID: {app_id}")
            
            # Проверяем доступность библиотеки
            try:
                from google_play_scraper import Sort, reviews_all
                print("Библиотека google-play-scraper доступна")
            except ImportError as e:
                print(f"Ошибка импорта библиотеки: {e}")
                return error_response(500, 
                    "Библиотека google-play-scraper недоступна. Проверьте requirements.txt",
                    headers
                )
            
            # Пробуем получить отзывы
            print(f"Начинаем сбор отзывов для {app_id}...")
            
            try:
                # Тестовый вызов - сначала попробуем получить 5 отзывов
                from google_play_scraper import reviews
                
                result, _ = reviews(
                    app_id,
                    lang='ru',
                    country='ru',
                    sort=Sort.NEWEST,
                    count=5  # Начинаем с малого для теста
                )
                
                print(f"Успешно получено {len(result)} тестовых отзывов")
                
                # Формируем тестовый CSV
                csv_content = create_test_csv(result, app_id)
                
                headers.update({
                    'Content-Type': 'text/csv; charset=utf-8',
                    'Content-Disposition': f'attachment; filename="test_reviews_{app_id}.csv"'
                })
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': csv_content
                }
                
            except Exception as e:
                print(f"Ошибка при получении отзывов: {e}")
                traceback.print_exc()
                
                # Пробуем предоставить полезную информацию об ошибке
                error_msg = str(e).lower()
                if "not found" in error_msg or "404" in error_msg:
                    return error_response(404, 
                        f"Приложение с ID '{app_id}' не найдено в Google Play",
                        headers
                    )
                elif "connection" in error_msg or "timeout" in error_msg:
                    return error_response(503, 
                        "Ошибка подключения к Google Play. Попробуйте позже.",
                        headers
                    )
                else:
                    return error_response(500, 
                        f"Ошибка при получении отзывов: {str(e)[:200]}",
                        headers
                    )
        
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            traceback.print_exc()
            return error_response(500, f"Внутренняя ошибка сервера: {str(e)}", headers)
    
    # Для других методов
    return error_response(405, "Метод не поддерживается", headers)


def extract_app_id(url):
    """Извлекает ID приложения из URL."""
    if not url:
        return None
    
    url = url.strip()
    
    # Паттерны для извлечения app_id
    patterns = [
        r'id=([a-zA-Z0-9\._]+)',
        r'/details\?id=([a-zA-Z0-9\._]+)',
        r'store/apps/details\?id=([a-zA-Z0-9\._]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # Если это уже app_id (например, com.whatsapp)
    if re.match(r'^[a-zA-Z0-9\._]+$', url) and '.' in url:
        return url
    
    return None


def create_test_csv(reviews_data, app_id):
    """Создает тестовый CSV из отзывов."""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow(['App ID', 'User Name', 'Rating', 'Date', 'Title', 'Content'])
    
    # Данные
    for review in reviews_data:
        writer.writerow([
            app_id,
            review.get('userName', ''),
            review.get('score', 0),
            review.get('at', '').strftime('%Y-%m-%d %H:%M:%S') if review.get('at') else '',
            review.get('title', ''),
            review.get('content', '')
        ])
    
    return output.getvalue()


def error_response(status_code, message, base_headers):
    """Создает JSON ответ с ошибкой."""
    headers = base_headers.copy()
    headers['Content-Type'] = 'application/json; charset=utf-8'
    
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps({
            "error": True,
            "message": message,
            "status": status_code
        }, ensure_ascii=False)
    }