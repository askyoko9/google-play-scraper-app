def handler(event, context):
    print("=== Python функция запущена ===")
    print(f"Метод: {event.get('httpMethod')}")
    print(f"Путь: {event.get('path')}")
    
    # Всегда возвращаем простой текстовый ответ
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/plain; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
        },
        'body': '✅ Python функция работает!\n\nДля тестирования:\n1. GET /api/\n2. POST /api/ с JSON\n\nPython 3.9 на Vercel'
    }