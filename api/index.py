import json
import re
import sys
import traceback
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

def handler(event, context):
    print("=" * 60)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] НОВЫЙ ЗАПРОС")
    print(f"Метод: {event.get('httpMethod')}")
    print(f"Путь: {event.get('path')}")
    print(f"Заголовки: {dict(event.get('headers', {}))}")
    
    # Базовые заголовки CORS
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
            "status": "success",
            "service": "Google Play Reviews Scraper API",
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "endpoints": {
                "GET /api/": "Эта информация",
                "POST /api/": "Сбор отзывов (JSON с полем 'url')"
            },
            "example_request": {
                "url": "https://play.google.com/store/apps/details?id=com.whatsapp"
            },
            "filters": "Последние 100 отзывов из РФ за последний год",
            "output": "CSV файл",
            "health": "ok"
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response, ensure_ascii=False, indent=2)
        }
    
    # POST запрос - основная логика
    if event.get('httpMethod') == 'POST':
        return handle_post_request(event, headers)
    
    # Для других методов
    return error_response(405, "Метод не поддерживается", headers)


def handle_post_request(event, headers):
    """Обработка POST запроса."""
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
                f"Не удалось извлечь ID приложения из URL\n"
                f"Примеры правильных форматов:\n"
                f"• https://play.google.com/store/apps/details?id=com.whatsapp\n"
                f"• com.whatsapp\n"
                f"• com.instagram.android",
                headers
            )
        
        print(f"Извлечен App ID: {app_id}")
        
        # Импортируем библиотеку
        try:
            from google_play_scraper import Sort, reviews
            print("✅ Библиотека google-play-scraper доступна")
        except ImportError as e:
            print(f"❌ Ошибка импорта библиотеки: {e}")
            traceback.print_exc()
            return error_response(500, 
                "Библиотека google-play-scraper недоступна\n"
                "Проверьте, что requirements.txt содержит: google-play-scraper==1.2.3",
                headers
            )
        
        # Получаем отзывы
        print(f"📥 Начинаем сбор отзывов для {app_id}...")
        
        try:
            # Получаем отзывы
            result, continuation_token = reviews(
                app_id,
                lang='ru',
                country='ru',
                sort=Sort.NEWEST,
                count=50  # Начинаем с 50 отзывов
            )
            
            print(f"✅ Успешно получено {len(result)} отзывов")
            
            if len(result) == 0:
                return error_response(404, 
                    f"Для приложения '{app_id}' не найдено отзывов на русском языке",
                    headers
                )
            
            # Формируем CSV
            csv_content = create_csv(result, app_id)
            
            headers.update({
                'Content-Type': 'text/csv; charset=utf-8',
                'Content-Disposition': f'attachment; filename="reviews_{app_id}_{datetime.now().strftime("%Y%m%d_%H%M")}.csv"'
            })
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': csv_content
            }
            
        except Exception as e:
            print(f"❌ Ошибка при получении отзывов: {e}")
            traceback.print_exc()
            
            # Анализируем ошибку
            error_msg = str(e).lower()
            if "not found" in error_msg or "404" in error_msg:
                return error_response(404, 
                    f"Приложение с ID '{app_id}' не найдено в Google Play Store",
                    headers
                )
            elif "connection" in error_msg or "timeout" in error_msg or "network" in error_msg:
                return error_response(503, 
                    "Ошибка подключения к Google Play. Возможные причины:\n"
                    "1. Проблемы с сетью\n"
                    "2. Google Play недоступен в вашем регионе\n"
                    "3. Превышено время ожидания",
                    headers
                )
            elif "permission" in error_msg or "access" in error_msg:
                return error_response(403, 
                    f"Нет доступа к приложению '{app_id}'",
                    headers
                )
            else:
                return error_response(500, 
                    f"Ошибка при получении отзывов: {str(e)[:200]}",
                    headers
                )
    
    except Exception as e:
        print(f"💥 Неожиданная ошибка: {e}")
        traceback.print_exc()
        return error_response(500, f"Внутренняя ошибка сервера: {str(e)}", headers)


def extract_app_id(url):
    """Извлекает ID приложения из URL."""
    if not url:
        return None
    
    url = url.strip()
    
    # Удаляем возможные пробелы и кавычки
    url = url.replace('"', '').replace("'", '')
    
    # Паттерны для извлечения app_id
    patterns = [
        r'id=([a-zA-Z0-9\._]+)',  # id=com.example.app
        r'appId=([a-zA-Z0-9\._]+)',  # appId=com.example.app
        r'/details\?id=([a-zA-Z0-9\._]+)',  # /details?id=com.example.app
        r'store/apps/details\?id=([a-zA-Z0-9\._]+)',  # store/apps/details?id=com.example.app
        r'play\.google\.com/store/apps/details\?id=([a-zA-Z0-9\._]+)'  # полный URL
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            app_id = match.group(1)
            print(f"Найден App ID по паттерну '{pattern}': {app_id}")
            return app_id
    
    # Если это уже app_id (например, com.whatsapp)
    if re.match(r'^[a-zA-Z0-9\._]+$', url) and '.' in url:
        print(f"Предполагаем, что это уже App ID: {url}")
        return url
    
    # Пробуем извлечь из короткой ссылки
    if 'play.google.com' in url and not 'details' in url:
        # Пробуем найти app_id в конце URL
        parts = url.split('/')
        for part in parts[::-1]:  # Идем с конца
            if re.match(r'^[a-zA-Z0-9\._]+$', part) and '.' in part:
                print(f"Извлечен App ID из пути: {part}")
                return part
    
    print(f"Не удалось извлечь App ID из: {url}")
    return None


def create_csv(reviews_data, app_id):
    """Создает CSV из отзывов."""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    
    # Заголовки
    writer.writerow([
        'App ID',
        'User Name', 
        'Rating',
        'Date',
        'Title',
        'Content',
        'Country',
        'Language'
    ])
    
    # Данные
    for review in reviews_data:
        # Безопасное извлечение данных
        user_name = str(review.get('userName', '')).replace('\n', ' ').replace('\r', ' ')
        rating = review.get('score', 0)
        
        # Обработка даты
        date_str = ''
        if review.get('at'):
            try:
                date_str = review['at'].strftime('%Y-%m-%d %H:%M:%S')
            except:
                date_str = str(review['at'])
        
        title = str(review.get('title', '')).replace('\n', ' ').replace('\r', ' ')
        content = str(review.get('content', '')).replace('\n', ' ').replace('\r', ' ')
        
        writer.writerow([
            app_id,
            user_name[:100],  # Ограничиваем длину
            rating,
            date_str,
            title[:200],
            content[:1000],
            'RU',
            'ru'
        ])
    
    csv_content = output.getvalue()
    print(f"Создан CSV размером {len(csv_content)} байт")
    return csv_content


def error_response(status_code, message, base_headers):
    """Создает JSON ответ с ошибкой."""
    headers = base_headers.copy()
    headers['Content-Type'] = 'application/json; charset=utf-8'
    
    response = {
        "error": True,
        "status": status_code,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"Возвращаем ошибку {status_code}: {message}")
    
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(response, ensure_ascii=False, indent=2)
    }