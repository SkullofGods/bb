// Тот же сервер, что и server.py, только на Node.
//
// Нужен для хостинга: в репозитории почти всё — картинки, json и js из webapp,
// поэтому автоопределение принимает проект за Node-приложение и Python не
// запускает. С этим файлом приложение поднимется в любом случае: по своему
// Dockerfile через server.py или автоопределением через `npm start`.
//
// Зависимостей нет, только стандартная библиотека.
//
//   node server.js          порт 3000 (или из PORT)
//   node server.js 9000     другой порт

'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, 'webapp');
const PORT = Number(process.argv[2] || process.env.PORT || 3000);

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.webp': 'image/webp',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain; charset=utf-8',
};
const LONG_CACHE = new Set(['.webp', '.png', '.jpg', '.jpeg', '.svg', '.ico']);

function send(res, code, body, headers) {
  res.writeHead(code, headers || { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end(body);
}

function serveFile(res, file) {
  const ext = path.extname(file).toLowerCase();
  fs.stat(file, (err, st) => {
    if (err || !st.isFile()) {
      send(res, 404, 'not found');
      return;
    }
    res.writeHead(200, {
      'Content-Type': TYPES[ext] || 'application/octet-stream',
      'Content-Length': st.size,
      'Cache-Control': LONG_CACHE.has(ext) ? 'public, max-age=604800' : 'no-cache',
    });
    fs.createReadStream(file).pipe(res);
  });
}

const server = http.createServer((req, res) => {
  let urlPath;
  try {
    urlPath = decodeURIComponent((req.url || '/').split('?')[0]);
  } catch (e) {
    send(res, 400, 'bad request');
    return;
  }

  if (urlPath === '/health' || urlPath === '/healthz') {
    send(res, 200, 'ok');
    return;
  }

  // не выпускаем за пределы webapp
  const rel = path.normalize(urlPath).replace(/^(\.\.[/\\])+/, '');
  let file = path.join(ROOT, rel);
  if (!file.startsWith(ROOT)) {
    send(res, 403, 'forbidden');
    return;
  }

  if (urlPath.endsWith('/')) {
    file = path.join(file, 'index.html');
  }
  fs.stat(file, (err, st) => {
    // неизвестный путь без расширения — отдаём приложение, оно одностраничное
    if ((err || st.isDirectory()) && !path.extname(file)) {
      serveFile(res, path.join(ROOT, 'index.html'));
      return;
    }
    serveFile(res, file);
  });
});

function shutdown(signal) {
  console.log(`Получен сигнал ${signal}, останавливаюсь`);
  server.close(() => {
    console.log('Сервер остановлен');
    process.exit(0);
  });
  setTimeout(() => process.exit(0), 5000).unref();
}
process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

if (!fs.existsSync(ROOT)) {
  console.error(`Нет папки с приложением: ${ROOT}`);
  process.exit(1);
}

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Мини-приложение слушает 0.0.0.0:${PORT}`);
  console.log(`Локально: http://localhost:${PORT}`);
});
