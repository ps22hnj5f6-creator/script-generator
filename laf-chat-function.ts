// Laf 云函数 — 一键部署（含 HTML 页面 + DeepSeek 代理）
// 函数名：chat
// 
// 部署步骤：
// 1. 在 Laf 控制台 → 云存储 → 创建桶「public」，权限设为 readonly
// 2. 上传「短视频稿生成器.html」，重命名为 index.html
// 3. 在 Laf 控制台 → 云函数 → 新建函数「chat」，粘贴此代码，发布
// 4. 访问 https://你的应用ID.laf.run/chat 即可使用

import cloud from '@lafjs/cloud'

export default async function (ctx: FunctionContext) {
  // ====== POST 请求 → DeepSeek API 代理 ======
  if (ctx.request.method === 'POST') {
    ctx.response.setHeader('Access-Control-Allow-Origin', '*');
    ctx.response.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    ctx.response.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

    try {
      const body = ctx.body;
      const authHeader = ctx.headers['authorization'] || '';

      const response = await fetch('https://api.deepseek.com/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': authHeader,
        },
        body: JSON.stringify(body),
      });

      const data = await response.json();
      ctx.response.status(response.status);
      return data;
    } catch (err) {
      ctx.response.status(500);
      return { error: '代理请求失败', detail: err.message };
    }
  }

  // ====== OPTIONS 预检请求 ======
  if (ctx.request.method === 'OPTIONS') {
    ctx.response.setHeader('Access-Control-Allow-Origin', '*');
    ctx.response.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    ctx.response.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    ctx.response.status(204);
    return '';
  }

  // ====== GET 请求 → 返回 HTML 页面 ======
  ctx.response.setHeader('Content-Type', 'text/html; charset=utf-8');
  const bucket = cloud.storage.bucket('public');
  const file = await bucket.readFile('index.html');
  return file;
}
