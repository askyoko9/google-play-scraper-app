// В Node.js функциях Vercel нужно экспортировать хэндлер по умолчанию
export default async function handler(request, response) {
    // Разрешаем CORS
    response.setHeader('Access-Control-Allow-Origin', '*');
    response.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    response.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    response.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    
    // Обработка OPTIONS запроса (preflight CORS)
    if (request.method === 'OPTIONS') {
        return response.status(200).end();
    }
    
    // GET запрос - информация о сервисе
    if (request.method === 'GET') {
        return response.status(200).json({
            status: 'success',
            service: 'Google Play Reviews Scraper',
            version: '1.0',
            message: 'Используйте POST запрос с { "url": "ссылка_на_приложение" }',
            example: {
                url: 'com.whatsapp'
            }
        });
    }
    
    // POST запрос - основная логика
    if (request.method === 'POST') {
        try {
            // Парсим тело запроса
            const body = await parseBody(request);
            
            if (!body || !body.url) {
                return response.status(400).json({
                    error: true,
                    message: 'Требуется поле "url" в теле запроса'
                });
            }
            
            const url = body.url.trim();
            
            // Извлекаем appId
            const appId = extractAppId(url);
            
            if (!appId) {
                return response.status(400).json({
                    error: true,
                    message: 'Не удалось извлечь ID приложения из URL. Примеры: com.whatsapp или https://play.google.com/store/apps/details?id=com.whatsapp'
                });
            }
            
            // Создаем демо-данные (в реальном приложении здесь будет парсинг)
            const reviews = generateDemoReviews(appId);
            
            // Создаем CSV
            const csv = generateCSV(reviews, appId);
            
            // Возвращаем CSV файл
            response.setHeader('Content-Type', 'text/csv; charset=utf-8');
            response.setHeader('Content-Disposition', `attachment; filename="reviews_${appId}.csv"`);
            
            return response.status(200).send(csv);
            
        } catch (error) {
            console.error('Error:', error);
            return response.status(500).json({
                error: true,
                message: `Внутренняя ошибка сервера: ${error.message}`
            });
        }
    }
    
    // Метод не поддерживается
    return response.status(405).json({
        error: true,
        message: 'Метод не поддерживается. Используйте GET или POST'
    });
}

// Функция для парсинга тела запроса
async function parseBody(request) {
    return new Promise((resolve, reject) => {
        let body = '';
        
        request.on('data', chunk => {
            body += chunk.toString();
        });
        
        request.on('end', () => {
            try {
                if (!body) return resolve({});
                resolve(JSON.parse(body));
            } catch (error) {
                reject(error);
            }
        });
        
        request.on('error', reject);
    });
}

// Извлечение appId из URL
function extractAppId(url) {
    const cleanUrl = url.trim();
    
    // Паттерны для извлечения appId
    const patterns = [
        /id=([a-zA-Z0-9\._]+)/i,
        /\/details\?id=([a-zA-Z0-9\._]+)/i,
        /store\/apps\/details\?id=([a-zA-Z0-9\._]+)/i,
        /play\.google\.com\/store\/apps\/details\?id=([a-zA-Z0-9\._]+)/i
    ];
    
    for (const pattern of patterns) {
        const match = cleanUrl.match(pattern);
        if (match && match[1]) {
            return match[1];
        }
    }
    
    // Если это уже appId (com.whatsapp)
    if (/^[a-zA-Z0-9\._]+$/.test(cleanUrl) && cleanUrl.includes('.')) {
        return cleanUrl;
    }
    
    return null;
}

// Генерация демо-отзывов
function generateDemoReviews(appId) {
    const now = new Date();
    const reviews = [];
    
    const demoData = [
        {
            userName: 'Анна Петрова',
            score: 5,
            title: 'Отличное приложение!',
            content: 'Очень удобно, все функции работают прекрасно. Пользуюсь каждый день.'
        },
        {
            userName: 'Иван Сидоров',
            score: 4,
            title: 'Хорошо, но есть недостатки',
            content: 'В целом нравится, но иногда приложение зависает. Добавьте темную тему.'
        },
        {
            userName: 'Мария Иванова',
            score: 5,
            title: 'Лучшее в своем роде',
            content: 'Пользуюсь уже год, никаких нареканий. Разработчики молодцы!'
        },
        {
            userName: 'Алексей Козлов',
            score: 3,
            title: 'Средненько',
            content: 'Есть более удобные аналоги. Интерфейс немного устаревший.'
        },
        {
            userName: 'Ольга Смирнова',
            score: 5,
            title: 'Супер!',
            content: 'Всё работает отлично, обновления регулярные. Рекомендую!'
        }
    ];
    
    demoData.forEach((review, index) => {
        const date = new Date(now);
        date.setDate(date.getDate() - index * 2); // Разные даты
        
        reviews.push({
            ...review,
            at: date.toISOString(),
            country: 'RU'
        });
    });
    
    return reviews;
}

// Генерация CSV
function generateCSV(reviews, appId) {
    const headers = ['App ID', 'Имя пользователя', 'Рейтинг', 'Дата', 'Заголовок', 'Текст отзыва', 'Страна'];
    
    const rows = reviews.map(review => {
        const date = new Date(review.at);
        const formattedDate = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
        
        // Экранируем кавычки для CSV
        const escapeCSV = (str) => {
            if (!str) return '';
            return `"${str.replace(/"/g, '""')}"`;
        };
        
        return [
            appId,
            escapeCSV(review.userName),
            review.score,
            formattedDate,
            escapeCSV(review.title),
            escapeCSV(review.content),
            review.country
        ];
    });
    
    return [headers, ...rows]
        .map(row => row.join(','))
        .join('\n');
}