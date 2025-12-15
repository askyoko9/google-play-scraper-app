export default async function handler(req, res) {
    // Устанавливаем CORS заголовки
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    // Обработка OPTIONS запроса (preflight CORS)
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }
    
    // GET запрос
    if (req.method === 'GET') {
        return res.status(200).json({
            status: 'success',
            service: 'Google Play Reviews Scraper',
            version: '1.0',
            message: 'Используйте POST запрос с JSON {"url": "ссылка_на_приложение"}',
            example: {
                url: 'com.whatsapp'
            }
        });
    }
    
    // POST запрос
    if (req.method === 'POST') {
        try {
            // Парсим тело запроса
            let body = '';
            await new Promise((resolve) => {
                req.on('data', chunk => {
                    body += chunk.toString();
                });
                req.on('end', resolve);
            });
            
            const data = JSON.parse(body || '{}');
            
            if (!data.url) {
                return res.status(400).json({
                    error: true,
                    message: 'Требуется поле "url" в теле запроса'
                });
            }
            
            // Извлекаем appId
            const appId = extractAppId(data.url.trim());
            
            if (!appId) {
                return res.status(400).json({
                    error: true,
                    message: 'Не удалось извлечь ID приложения. Примеры: com.whatsapp или https://play.google.com/store/apps/details?id=com.whatsapp'
                });
            }
            
            // Генерируем демо-данные
            const reviews = generateDemoData(appId);
            
            // Создаем CSV
            const csv = generateCSV(reviews, appId);
            
            // Возвращаем CSV файл
            res.setHeader('Content-Type', 'text/csv; charset=utf-8');
            res.setHeader('Content-Disposition', `attachment; filename="reviews_${appId}.csv"`);
            
            return res.status(200).send(csv);
            
        } catch (error) {
            console.error('Error:', error);
            return res.status(500).json({
                error: true,
                message: `Внутренняя ошибка: ${error.message}`
            });
        }
    }
    
    // Метод не поддерживается
    return res.status(405).json({
        error: true,
        message: 'Метод не поддерживается'
    });
}

function extractAppId(url) {
    if (!url) return null;
    
    const cleanUrl = url.trim();
    
    // Паттерны для извлечения appId
    const patterns = [
        /id=([a-zA-Z0-9\._]+)/i,
        /\/details\?id=([a-zA-Z0-9\._]+)/i,
        /store\/apps\/details\?id=([a-zA-Z0-9\._]+)/i
    ];
    
    for (const pattern of patterns) {
        const match = cleanUrl.match(pattern);
        if (match && match[1]) {
            return match[1];
        }
    }
    
    // Если это уже appId
    if (/^[a-zA-Z0-9\._]+$/.test(cleanUrl) && cleanUrl.includes('.')) {
        return cleanUrl;
    }
    
    return null;
}

function generateDemoData(appId) {
    const now = new Date();
    const reviews = [];
    
    const templates = [
        {
            userName: 'Александр Петров',
            score: 5,
            title: 'Отличное приложение!',
            content: 'Очень удобный интерфейс, все работает быстро и без глюков.'
        },
        {
            userName: 'Мария Иванова',
            score: 4,
            title: 'Хорошо, но можно лучше',
            content: 'Нравится функционал, но не хватает некоторых функций.'
        },
        {
            userName: 'Сергей Сидоров',
            score: 5,
            title: 'Лучшее в своем роде',
            content: 'Пользуюсь каждый день, очень доволен.'
        },
        {
            userName: 'Ольга Козлова',
            score: 3,
            title: 'Средненько',
            content: 'Есть более удобные аналоги, но это тоже неплохо.'
        },
        {
            userName: 'Дмитрий Новиков',
            score: 5,
            title: 'Супер!',
            content: 'Разработчики молодцы, постоянно обновляют и улучшают.'
        },
        {
            userName: 'Екатерина Васнецова',
            score: 4,
            title: 'Удобно и понятно',
            content: 'Интуитивно понятный интерфейс, легко разобраться.'
        },
        {
            userName: 'Анна Смирнова',
            score: 5,
            title: 'Рекомендую всем!',
            content: 'Использую уже полгода, ни разу не пожалела.'
        },
        {
            userName: 'Михаил Орлов',
            score: 2,
            title: 'Не очень',
            content: 'Часто вылетает, нужно дорабатывать.'
        },
        {
            userName: 'Татьяна Волкова',
            score: 5,
            title: 'Идеально!',
            content: 'Все функции на месте, работает стабильно.'
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
    const headers = ['App ID', 'Имя пользователя', 'Рейтинг', 'Дата', 'Заголовок', 'Текст отзыва', 'Страна'];
    
    const rows = reviews.map(review => {
        const date = new Date(review.at);
        const dateStr = date.toLocaleDateString('ru-RU') + ' ' + date.toLocaleTimeString('ru-RU');
        
        // Экранирование для CSV
        const escape = (str) => {
            if (str === null || str === undefined) return '';
            return `"${String(str).replace(/"/g, '""')}"`;
        };
        
        return [
            appId,
            escape(review.userName),
            review.score,
            escape(dateStr),
            escape(review.title),
            escape(review.content),
            review.country
        ];
    });
    
    return [headers, ...rows]
        .map(row => row.join(','))
        .join('\n');
}