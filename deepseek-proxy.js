/**
 * DeepSeek CORS Proxy
 * 解决浏览器端直接调用 DeepSeek API 的跨域问题
 * 
 * 用法: node deepseek-proxy.js
 * 默认监听 http://localhost:3001
 */

const http = require('http');

const PORT = process.env.PORT || 3001;
const DEEPSEEK_BASE = 'https://api.deepseek.com';

const server = http.createServer(async (req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  // Preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // 只代理 /chat/completions
  if (req.method !== 'POST' || req.url !== '/chat/completions') {
    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Not Found. Use POST /chat/completions' }));
    return;
  }

  // 读取请求体
  let body = '';
  try {
    for await (const chunk of req) {
      body += chunk;
    }
  } catch (e) {
    res.writeHead(400);
    res.end(JSON.stringify({ error: 'Failed to read request body' }));
    return;
  }

  try {
    // 转发到 DeepSeek
    const deepseekResp = await fetch(DEEPSEEK_BASE + '/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': req.headers['authorization'] || ''
      },
      body: body
    });

    const data = await deepseekResp.json();

    res.writeHead(deepseekResp.status, {
      'Content-Type': 'application/json'
    });
    res.end(JSON.stringify(data));
  } catch (err) {
    console.error('Proxy error:', err.message);
    res.writeHead(502);
    res.end(JSON.stringify({ error: { message: '代理请求失败: ' + err.message } }));
  }
});

server.listen(PORT, () => {
  console.log(`🔁 DeepSeek CORS 代理已启动: http://localhost:${PORT}`);
  console.log(`   所有请求 POST http://localhost:${PORT}/chat/completions → api.deepseek.com`);
  console.log(`   按 Ctrl+C 停止`);
});
