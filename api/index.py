import json

def handler(request):
    print("=== PYTHON FUNCTION IS RUNNING ===")
    
    # Всегда возвращаем простой текстовый ответ
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/plain; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
        },
        'body': '✅ Python функция работает!'
    }