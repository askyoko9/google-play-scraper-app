import json
import re
import traceback
from datetime import datetime, timedelta
import sys
import os

print("=" * 60)
print("Python version:", sys.version)
print("Current directory:", os.getcwd())
print("Files in api directory:", os.listdir('.'))
print("=" * 60)

def handler(event, context):
    """Основной обработчик для Vercel."""
    try:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] НОВЫЙ ЗАПРОС")
        print(f"Method: {event.get('httpMethod')}")
        print(f"Path: {event.get('path')}")
        print(f"Headers: {event.get('headers', {})}")
        
        # Устанавливаем CORS заголовки
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Cache-Control': 'no-cache, no-store, must-revalidate'
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
            
            response_data = {
                "status": "success",
                "service": "Google Play Reviews Scraper API",
                "version": "1.0",
                "timestamp": datetime.now().isoformat(),
                "environment": "Python on Vercel",
                "endpoints": {
                    "GET /api/": "Информация о сервисе",
                    "POST /api/": "Сбор отзывов (требуется JSON с полем 'url')"
                },
                "example": {
                    "url": "https://play.google.com/store/apps/details?id=com.whatsapp"
                },
                "features": [
                    "Сбор до 100 отзывов",
                    "Русский язык (ru)",
                    "Российский регион (ru)",
                    "Фильтр: последний год",
                    "Сортировка: новые первыми",
                    "Формат вывода: CSV"
                ]
            }
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(response_data, ensure_ascii=False, indent=2)
            }
        
        # POST запрос - сбор отзывов
        if event.get('httpMethod') == 'POST':
            return handle_post_request(event, headers)
        
        # Метод не поддерживается
        return {
            'statusCode': 405,
            'headers': headers,
            'body': json.dumps({
                "error": "Method not allowed",
                "message": "Используйте GET или POST методы"
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                "error": "Internal server error",
                "message": str(e)
            }, ensure_ascii=False)
        }


def handle_post_request(event, base_headers):
    """Обработка POST запроса."""
    try:
        # Получаем тело запроса
        body = event.get('body', '{}')
        print(f"Request body: {body[:500]}...")
        
        # Парсим JSON
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            return error_response(400, f"Invalid JSON format: {str(e)}", base_headers)
        
        # Проверяем наличие URL
        if 'url' not in data:
            return error_response(400, "Missing 'url' field in JSON", base_headers)
        
        url = data['url'].strip()
        if not url:
            return error_response(400, "URL cannot be empty", base_headers)
        
        print(f"Received URL: {url}")
        
        # Извлекаем App ID
        app_id = extract_app_id(url)
        if not app_id:
            return error_response(400, 
                f"Could not extract app ID from URL\n"
                f"Valid formats:\n"
                f"• https://play.google.com/store/apps/details?id=com.example.app\n"
                f"• com.example.app",
                base_headers
            )
        
        print(f"Extracted App ID: {app_id}")
        
        # Пробуем импортировать библиотеку
        try:
            from google_play_scraper import Sort, reviews
            print("✓ google-play-scraper library is available")
        except ImportError as e:
            print(f"✗ Failed to import google-play-scraper: {e}")
            traceback.print_exc()
            return error_response(500, 
                "Scraping library not available. Please check requirements.txt",
                base_headers
            )
        
        # Получаем отзывы
        print(f"Fetching reviews for {app_id}...")
        
        try:
            # Получаем первые 20 отзывов для теста
            result, _ = reviews(
                app_id,
                lang='ru',
                country='ru',
                sort=Sort.NEWEST,
                count=20
            )
            
            print(f"✓ Successfully fetched {len(result)} reviews")
            
            if len(result) == 0:
                return error_response(404, 
                    f"No reviews found for app '{app_id}' in Russian language",
                    base_headers
                )
            
            # Создаем CSV
            csv_content = create_csv(result, app_id)
            
            headers = base_headers.copy()
            headers.update({
                'Content-Type': 'text/csv; charset=utf-8',
                'Content-Disposition': f'attachment; filename="reviews_{app_id}.csv"'
            })
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': csv_content
            }
            
        except Exception as e:
            print(f"✗ Error fetching reviews: {e}")
            traceback.print_exc()
            
            error_msg = str(e).lower()
            if "not found" in error_msg:
                return error_response(404, 
                    f"App '{app_id}' not found in Google Play Store",
                    base_headers
                )
            elif "connection" in error_msg or "timeout" in error_msg:
                return error_response(503, 
                    "Connection error to Google Play. Please try again later.",
                    base_headers
                )
            else:
                return error_response(500, 
                    f"Error while fetching reviews: {str(e)[:200]}",
                    base_headers
                )
    
    except Exception as e:
        print(f"✗ Unexpected error in POST handler: {e}")
        traceback.print_exc()
        return error_response(500, f"Internal server error: {str(e)}", base_headers)


def extract_app_id(url):
    """Extract app ID from URL."""
    if not url:
        return None
    
    url = url.strip()
    
    # Patterns to extract app ID
    patterns = [
        r'id=([a-zA-Z0-9\._]+)',
        r'/details\?id=([a-zA-Z0-9\._]+)',
        r'store/apps/details\?id=([a-zA-Z0-9\._]+)',
        r'play\.google\.com/store/apps/details\?id=([a-zA-Z0-9\._]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # If it's already an app ID (e.g., com.whatsapp)
    if re.match(r'^[a-zA-Z0-9\._]+$', url) and '.' in url:
        return url
    
    return None


def create_csv(reviews_data, app_id):
    """Create CSV from reviews data."""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    
    # Headers
    writer.writerow(['App ID', 'User', 'Rating', 'Date', 'Title', 'Review'])
    
    # Data
    for review in reviews_data:
        user = review.get('userName', 'Anonymous')
        rating = review.get('score', 0)
        
        # Format date
        date_str = ''
        if review.get('at'):
            try:
                date_str = review['at'].strftime('%Y-%m-%d %H:%M:%S')
            except:
                date_str = str(review['at'])
        
        title = review.get('title', '')
        content = review.get('content', '')
        
        # Clean text
        user = str(user).replace('\n', ' ').replace('\r', ' ').strip()
        title = str(title).replace('\n', ' ').replace('\r', ' ').strip()
        content = str(content).replace('\n', ' ').replace('\r', ' ').strip()
        
        writer.writerow([
            app_id,
            user[:100],
            rating,
            date_str,
            title[:200],
            content[:500]
        ])
    
    return output.getvalue()


def error_response(status_code, message, base_headers):
    """Create error response."""
    headers = base_headers.copy()
    headers['Content-Type'] = 'application/json; charset=utf-8'
    
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps({
            "error": True,
            "status": status_code,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    }