import json
import traceback

def handler(event, context):
    """Упрощенный обработчик для тестирования"""
    try:
        print("=== НАЧАЛО ОБРАБОТКИ ===")
        print(f"HTTP метод: {event.get('httpMethod')}")
        print(f"Путь: {event.get('path')}")
        print(f"Заголовки: {event.get('headers', {})}")
        
        # Базовые заголовки CORS
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
        
        # Обработка OPTIONS (preflight CORS)
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': ''
            }
        
        # Обработка GET - тестовый ответ
        if event.get('httpMethod') == 'GET':
            response = {
                "status": "ok",
                "service": "Google Play Reviews Scraper",
                "message": "API работает корректно",
                "usage": "Отправьте POST запрос с JSON {'url': 'ваша_ссылка'}"
            }
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(response, ensure_ascii=False)
            }
        
        # Обработка POST - минимальная логика
        if event.get('httpMethod') == 'POST':
            body = event.get('body', '{}')
            
            try:
                data = json.loads(body)
            except:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({"error": "Неверный JSON"}, ensure_ascii=False)
                }
            
            # Простой тестовый ответ
            response = {
                "status": "success",
                "message": "Запрос получен",
                "received_url": data.get('url', 'не указан'),
                "next_step": "В реальной версии здесь будет сбор отзывов"
            }
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(response, ensure_ascii=False)
            }
        
        # Для других методов
        return {
            'statusCode': 405,
            'headers': headers,
            'body': json.dumps({"error": "Метод не поддерживается"}, ensure_ascii=False)
        }
        
    except Exception as e:
        print(f"!!! КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                "error": "Внутренняя ошибка сервера",
                "details": str(e)
            }, ensure_ascii=False)
        }