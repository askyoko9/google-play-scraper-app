// netlify/functions/scrapper.js (CommonJS)

// Вспомогательные функции, использующие CJS синтаксис
function extractAppId(url) {
    if (typeof url !== 'string' || !url) return null;
    
    const cleanUrl = url.trim();
    const match = cleanUrl.match(/id=([^&]+)/) || cleanUrl.match(/\/store\/apps\/details\/([^\?]+)/);
    
    if (match && match[1]) {
        // Убираем потенциальные 'id=' из начала
        return match[1].startsWith('id=') ? match[1].substring(3) : match[1];
    }
    return cleanUrl; // Если не нашли ID, возвращаем чистую строку
}

function generateDemoData(appId) {
    // Оригинальная функция генерации демо-данных
    // ... (Оставьте ваш оригинальный код generateDemoData здесь) ...
    const now = new Date();
    const reviews = [];
    const templates = [
        {
            userName: 'Иван Петров',
            score: 5,
            title: 'Отличное приложение',
            content: 'Все работает как часы, очень полезно!'
        },
        {
            userName: 'Елена Смирнова',
            score: 5,
            title: 'Надежный сервис',
            content: 'Использую несколько месяцев, работает стабильно.'
        },
        {
            userName: 'Павел Белов',
            score: 4,
            title: 'Хорошее приложение',
            content: 'В целом устраивает, но есть небольшие баги.'
        }
    ];
    
    templates.forEach((template, index) => {
        const date = new Date(now);
        date.setDate(date.getDate() - index);
        
        reviews.push({
            ...template,
            at: date.toISOString(),
            country: 'RU',
            appId: appId
        });
    });
    
    return reviews;
}

function generateCSV(reviews, appId) {
    // Оригинальная функция генерации CSV
    const headers = ['App ID', 'Имя пользователя', 'Рейтинг', 'Дата', 'Заголовок', 'Текст отзыва', 'Страна'];
    
    const rows = reviews.map(review => {
        const date = new Date(review.at);
        const dateStr = date.toLocaleDateString('ru-RU') + ' ' + date.toLocaleTimeString('ru-RU');
        
        // Экранирование для CSV
        const escape = (str) => {
            if (str === null || str === undefined) return '';
            // Замена двойных кавычек на две двойные и обрамление в кавычки
            return `"${String(str).replace(/"/g, '""')}"`;
        };
        
        return [
            appId,
            escape(review.userName),
            review.score,
            dateStr,
            escape(review.title),
            escape(review.content),
            review.country
        ];
    });
    
    return [headers, ...rows]
        .map(row => row.join(','))
        .join('\n');
}

// Главный обработчик, экспортирующий CJS
module.exports.handler = async function (event, context) {
    
    // Заголовки CORS для ответа AWS Gateway/Netlify
    const corsHeaders = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    };

    // OPTIONS запрос (Preflight)
    if (event.httpMethod === 'OPTIONS') {
        return { statusCode: 200, headers: corsHeaders, body: '' };
    }
    
    // GET запрос
    if (event.httpMethod === 'GET') {
        return {
            statusCode: 200,
            headers: corsHeaders,
            body: JSON.stringify({
                status: 'success',
                message: 'Используйте POST запрос с JSON {"url": "ссылка_на_приложение"}'
            })
        };
    }
    
    // POST запрос
    if (event.httpMethod === 'POST') {
        try {
            // Netlify (как и AWS Lambda) передает тело в event.body
            const data = JSON.parse(event.body || '{}');
            
            if (!data.url) {
                return {
                    statusCode: 400,
                    headers: corsHeaders,
                    body: JSON.stringify({ error: true, message: 'Требуется поле "url"' })
                };
            }
            
            const appId = extractAppId(data.url);
            
            if (!appId) {
                return {
                    statusCode: 400,
                    headers: corsHeaders,
                    body: JSON.stringify({ error: true, message: 'Не удалось извлечь App ID' })
                };
            }
            
            // 1. Получаем данные (здесь используем демо)
            const reviews = generateDemoData(appId);
            
            // 2. Генерируем CSV
            const csv = generateCSV(reviews, appId);
            
            // 3. Отправляем CSV в виде Base64 (стандарт Netlify/Lambda для бинарных данных)
            const filename = `reviews_${appId}.csv`;
            
            return {
                statusCode: 200,
                // Добавляем заголовки для скачивания файла
                headers: {
                    ...corsHeaders,
                    'Content-Type': 'text/csv; charset=utf-8',
                    'Content-Disposition': `attachment; filename="${filename}"`
                },
                body: csv, // Отправляем как текст (Netlify часто может обрабатывать его)
                isBase64Encoded: false // Указываем, что тело — это не Base64
            };
            
        } catch (error) {
            console.error('SERVER ERROR:', error);
            return {
                statusCode: 500,
                headers: corsHeaders,
                body: JSON.stringify({ error: true, message: `Внутренняя ошибка сервера: ${error.message}` })
            };
        }
    }

    // Если метод не GET/POST/OPTIONS
    return {
        statusCode: 405,
        headers: corsHeaders,
        body: JSON.stringify({ error: true, message: 'Method Not Allowed' })
    };
};