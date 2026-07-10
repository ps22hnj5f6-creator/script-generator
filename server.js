/**
 * 短视频引流稿生成器 — 线上版本服务器
 * 零依赖，Node.js 内置模块即可运行
 *
 * 用法: node server.js
 * 默认监听 http://localhost:3001
 */

const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3001;
const HTML_FILE = path.join(__dirname, '短视频稿生成器.html');

// MIME 类型
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js':   'application/javascript; charset=utf-8',
  '.css':  'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png':  'image/png',
  '.ico':  'image/x-icon',
};

// 静态文件服务
function serveStatic(req, res) {
  let filePath = req.url === '/' ? '/index.html' : req.url;
  // 兼容直接访问 HTML 文件名
  if (filePath.includes('短视频稿生成器')) {
    filePath = '/index.html';
  }

  const ext = path.extname(filePath);
  const contentType = MIME[ext] || 'application/octet-stream';

  // 如果是 /index.html，返回 HTML 文件
  const actualPath = path.join(__dirname, filePath === '/index.html' ? '短视频稿生成器.html' : filePath.substring(1));

  try {
    const content = fs.readFileSync(actualPath);
    res.writeHead(200, { 'Content-Type': contentType });
    res.end(content);
  } catch {
    // 404 → 也返回 HTML（SPA fallback）
    try {
      const html = fs.readFileSync(HTML_FILE);
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(html);
    } catch {
      res.writeHead(404);
      res.end('Not Found');
    }
  }
}

// DeepSeek API 代理
async function proxyDeepSeek(req, res) {
  // CORS（本地开发用）
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  if (req.method !== 'POST') {
    res.writeHead(405);
    res.end(JSON.stringify({ error: 'Method Not Allowed' }));
    return;
  }

  // 读取请求体
  let body = '';
  try {
    for await (const chunk of req) {
      body += chunk;
    }
  } catch {
    res.writeHead(400);
    res.end(JSON.stringify({ error: 'Bad Request' }));
    return;
  }

  try {
    const deepseekResp = await fetch('https://api.deepseek.com/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': req.headers['authorization'] || ''
      },
      body
    });

    const data = await deepseekResp.json();

    res.writeHead(deepseekResp.status, {
      'Content-Type': 'application/json'
    });
    res.end(JSON.stringify(data));
  } catch (err) {
    console.error('代理错误:', err.message);
    res.writeHead(502);
    res.end(JSON.stringify({ error: { message: '代理请求失败: ' + err.message } }));
  }
}

// 主服务器
const server = http.createServer(async (req, res) => {
  if (req.url === '/chat/completions') {
    return proxyDeepSeek(req, res);
  }
  return serveStatic(req, res);
});

server.listen(PORT, '0.0.0.0', () => {
  console.log('🚀 短视频引流稿生成器已上线');
  console.log('   监听地址: http://0.0.0.0:' + PORT);
  console.log('   模板模式: 直接使用');
  console.log('   AI 模式:  输入 DeepSeek API Key 后使用（已内置代理，无需额外启动）');
  console.log('   按 Ctrl+C 停止');
});
