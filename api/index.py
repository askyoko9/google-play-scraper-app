import re
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO
from flask import Flask, request, jsonify, send_file
from google_play_scraper import Sort, reviews_all

# Создаем экземпляр Flask
app = Flask(__name__)

# --- Вспомогательные функции для скрейпинга (те же, что и ранее) ---

def get_app_id(url):
    """Извлекает ID приложения из URL Google Play Store."""
    match = re.search(r'id=([^&]+)', url)
    if match:
        return match.group(1)
    return None

def scrape_reviews(app_id, count_limit=100, country_code='ru', days_limit=365):
    """
    Собирает, фильтрует и форматирует отзывы.
    Возвращает pandas DataFrame или None в случае ошибки.
    """
    date_cutoff = datetime.now() - timedelta(days=days_limit)
    
    try:
        # Собираем отзывы
        result = reviews_all(
            app_id,
            lang='ru',            # Язык
            country=country_code, # Страна (регион)
            sort=Sort.NEWEST,     # Сортировка
        )
        
        data_list = []
        for review in result:
            review_date = review['at'].replace(tzinfo=None)
            
            # Фильтрация по дате и лимиту
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
        
        return pd.DataFrame(data_list)

    except Exception as e:
        # Вариант B: Запись ошибки и продолжение/возврат None
        print(f"Ошибка при скрейпинге {app_id}: {e}")
        return None

# --- Основной маршрут Flask (Endpoint) ---

@app.route('/', methods=['POST'])
def handle_scrape():
    # 1. Получаем данные из POST-запроса (JSON)
    data = request.get_json(silent=True)
    if not data or 'url' not in data:
        return jsonify({"error": "Неверный формат запроса. Ожидается JSON с полем 'url'."}), 400

    app_url = data['url']
    app_id = get_app_id(app_url)

    if not app_id:
        return jsonify({"error": "Не удалось извлечь ID приложения из ссылки. Проверьте формат."}), 400

    # 2. Выполняем скрейпинг
    df = scrape_reviews(app_id) # Используем параметры по умолчанию (100 отзывов, ru, 365 дней)

    if df is None:
        return jsonify({"error": f"Не удалось получить отзывы для ID: {app_id}. Приложение не найдено или возникла ошибка API."}), 500
    
    if df.empty:
        return jsonify({"error": "Отзывы найдены, но ни один из них не соответствует фильтрам (РФ, 365 дней). Попробуйте другое приложение."}), 404

    # 3. Подготовка CSV для отправки
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8')
    csv_buffer.seek(0)
    
    filename = f"reviews_{app_id}_{datetime.now().strftime('%Y%m%d')}.csv"

    # 4. Возвращаем CSV как файл
    return send_file(
        csv_buffer,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename,
        max_age=0 # Отключаем кеширование
    )

# Этот блок нужен для локального тестирования, Vercel вызывает app.route напрямую
if __name__ == '__main__':
    app.run(debug=True)