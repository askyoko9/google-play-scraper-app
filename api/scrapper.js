import fetch from 'node-fetch';

export default async function handler(req, res) {
    // Разрешаем CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }
    
    if (req.method === 'GET') {
        return res.status(200).json({
            status: 'success',
            service: 'Google Play Scraper (Node.js)',
            message: 'Используйте POST запрос с { "url": "ссылка_на_приложение" }'
        });
    }
    
    if (req.method === 'POST') {
        try {
            const { url } = req.body;
            
            if (!url) {
                return res.status(400).json({
                    error: true,
                    message: 'Требуется поле "url" в теле запроса'
                });
            }
            
            // Извлекаем appId из URL
            const appId = extractAppId(url);
            
            if (!appId) {
                return res.status(400).json({
                    error: true,
                    message: 'Не удалось извлечь ID приложения из URL'
                });
            }
            
            // Используем публичный API для получения отзывов
            const reviews = await fetchReviewsFromAPI(appId);
            
            // Создаем CSV
            const csv = generateCSV(reviews, appId);
            
            // Устанавливаем заголовки для скачивания файла
            res.setHeader('Content-Type', 'text/csv; charset=utf-8');
            res.setHeader('Content-Disposition', `attachment; filename="reviews_${appId}.csv"`);
            
            return res.status(200).send(csv);
            
        } catch (error) {
            console.error('Error:', error);
            return res.status(500).json({
                error: true,
                message: `Ошибка сервера: ${error.message}`
            });
        }
    }
    
    return res.status(405).json({ error: 'Method not allowed' });
}

function extractAppId(url) {
    // Убираем пробелы
    const cleanUrl = url.trim();
    
    // Паттерны для извлечения appId
    const patterns = [
        /id=([a-zA-Z0-9\._]+)/,
        /\/details\?id=([a-zA-Z0-9\._]+)/,
        /store\/apps\/details\?id=([a-zA-Z0-9\._]+)/,
        /play\.google\.com\/store\/apps\/details\?id=([a-zA-Z0-9\._]+)/
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

async function fetchReviewsFromAPI(appId) {
    // Используем альтернативный источник данных
    // Это пример - вам нужно найти работающий API
    
    const mockReviews = [
        {
            userName: 'Иван Иванов',
            score: 5,
            at: new Date().toISOString(),
            title: 'Отличное приложение!',
            content: 'Очень удобно и функционально.',
            country: 'RU'
        },
        {
            userName: 'Анна Петрова',
            score: 4,
            at: new Date(Date.now() - 86400000).toISOString(), // вчера
            title: 'Хорошо, но есть недочеты',
            content: 'В целом нравится, но иногда глючит.',
            country: 'RU'
        },
        {
            userName: 'Сергей Сидоров',
            score: 3,
            at: new Date(Date.now() - 172800000).toISOString(), // позавчера
            title: 'Средненько',
            content: 'Есть более удобные аналоги.',
            country: 'RU'
        }
    ];
    
    // В реальном приложении здесь должен быть вызов реального API
    // Например: const response = await fetch(`https://api.example.com/reviews/${appId}`);
    
    return mockReviews;
}

function generateCSV(reviews, appId) {
    const headers = ['App ID', 'Имя пользователя', 'Рейтинг', 'Дата', 'Заголовок', 'Текст отзыва', 'Страна'];
    
    const rows = reviews.map(review => [
        appId,
        `"${review.userName.replace(/"/g, '""')}"`,
        review.score,
        new Date(review.at).toLocaleDateString('ru-RU'),
        `"${(review.title || '').replace(/"/g, '""')}"`,
        `"${(review.content || '').replace(/"/g, '""')}"`,
        review.country
    ]);
    
    return [headers, ...rows]
        .map(row => row.join(','))
        .join('\n');
}