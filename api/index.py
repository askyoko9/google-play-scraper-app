import json
import sys
import os

print("=" * 60)
print("DEBUG: Python function starting")
print("Python version:", sys.version)
print("Current directory:", os.getcwd())
print("Files in current dir:", os.listdir('.'))
print("=" * 60)

def handler(event, context):
    print("\n" + "=" * 60)
    print("DEBUG: handler() called")
    print(f"Event keys: {list(event.keys())}")
    print(f"HTTP Method: {event.get('httpMethod', 'NOT FOUND')}")
    print(f"Path: {event.get('path', 'NOT FOUND')}")
    
    try:
        # Всегда возвращаем успешный JSON ответ
        response = {
            "success": True,
            "message": "Python function is working!",
            "method": event.get('httpMethod', 'unknown'),
            "timestamp": "2024-01-01T00:00:00Z",  # Фиксированное время для теста
            "debug_info": {
                "python_version": sys.version.split()[0],
                "event_keys": list(event.keys())
            }
        }
        
        print(f"Returning response: {json.dumps(response)}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response, indent=2)
        }
        
    except Exception as e:
        print(f"ERROR in handler: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'text/plain',
                'Access-Control-Allow-Origin': '*'
            },
            'body': f'Error: {str(e)}'
        }