import json

def handler(event, context):
    print("=== ФУНКЦИЯ ВЫЗВАНА ===")
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            "success": True,
            "message": "Hello from Python function!",
            "method": event.get('httpMethod', 'UNKNOWN')
        })
    }