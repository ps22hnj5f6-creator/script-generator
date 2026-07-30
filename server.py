#!/usr/bin/env python3
"""
短视频稿生成器 — 本地服务器（Python 版，零依赖）
macOS 自带 Python 即可运行，无需安装任何东西

用法: python3 server.py
默认监听 http://localhost:3001
"""

import json
import os
import ssl
import sys
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# 创建跳过 SSL 验证的上下文（解决公司网络中间人代理/防火墙导致的证书问题）
_NO_VERIFY_SSL = ssl.create_default_context()
_NO_VERIFY_SSL.check_hostname = False
_NO_VERIFY_SSL.verify_mode = ssl.CERT_NONE

PORT = int(os.environ.get('PORT', '3001'))
BASE_DIR = Path(__file__).parent.resolve()
HTML_FILE = BASE_DIR / '短视频稿生成器.html'

# 让 fetch_hotlist 模块可被导入（同目录）
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


class Handler(BaseHTTPRequestHandler):
    """统一处理静态文件托管 + DeepSeek API 代理"""

    # 静默日志（不刷屏）
    def log_message(self, format, *args):
        if '/chat/completions' not in args[0] if args else True:
            sys.stderr.write(f"[server] {format % args}\n")

    # ====== CORS 预检 ======
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    # ====== DeepSeek API 代理 ======
    def do_POST(self):
        # 只代理 /chat/completions
        if self.path != '/chat/completions':
            self.send_error(405, 'Method Not Allowed')
            return

        # 读取请求体
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b'{}'

        # 转发到 DeepSeek
        req = urllib.request.Request(
            'https://api.deepseek.com/chat/completions',
            data=body,
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'Authorization': self.headers.get('Authorization', ''),
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=60, context=_NO_VERIFY_SSL) as resp:
                resp_data = resp.read()
                self.send_response(resp.status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(resp_data)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='replace')
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(err_body.encode())
        except Exception as e:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_json = json.dumps({'error': {'message': f'代理请求失败: {e}'}})
            self.wfile.write(error_json.encode())

    # ====== 热榜实时接口（点击「获取」实时刷新）======
    def do_GET(self):
        file_path = self.path.split('?', 1)[0]

        # 热榜实时拉取：聚合 5 源（抖音财经/财联社/36氪/微博 + 种子账号手动补充）
        if file_path == '/api/hotlist':
            self._serve_hotlist()
            return

        # 根路径 → HTML
        if file_path in ('/', '/index.html'):
            self._serve_file(HTML_FILE, 'text/html; charset=utf-8')
            return

        # 其他静态资源
        # 安全：防止路径穿越
        safe_path = (BASE_DIR / file_path.lstrip('/')).resolve()
        if not str(safe_path).startswith(str(BASE_DIR)):
            self.send_error(403, 'Forbidden')
            return

        if safe_path.exists() and safe_path.is_file():
            ext = safe_path.suffix.lower()
            mime_types = {
                '.html': 'text/html; charset=utf-8',
                '.js':   'application/javascript; charset=utf-8',
                '.css':  'text/css; charset=utf-8',
                '.json': 'application/json; charset=utf-8',
                '.png':  'image/png',
                '.svg':  'image/svg+xml',
                '.ico':  'image/x-icon',
            }
            ct = mime_types.get(ext, 'application/octet-stream')
            self._serve_file(safe_path, ct)
        else:
            # SPA fallback → 返回 HTML
            self._serve_file(HTML_FILE, 'text/html; charset=utf-8')

    def _serve_file(self, filepath, content_type):
        try:
            data = filepath.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_error(404, 'Not Found')

    # ====== 热榜实时聚合 ======
    def _serve_hotlist(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        try:
            from fetch_hotlist import build_hotlist
            data = build_hotlist()
            # 种子账号由前端本地粘贴，服务端不预置；字段保留为空数组
            if 'seedItems' not in data:
                data['seedItems'] = []
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            # 实时抓取整体失败 → 回退到每日快照 hotlist.json
            try:
                snap = (BASE_DIR / 'hotlist.json').read_text(encoding='utf-8')
                fallback = json.loads(snap)
                fallback['fetchedAt'] = fallback.get('updated_at', '') + '（快照兜底）'
                self.wfile.write(json.dumps(fallback, ensure_ascii=False).encode('utf-8'))
            except Exception:
                err = json.dumps({'error': f'热榜获取失败: {e}', 'items': [], 'seedItems': []})
                self.wfile.write(err.encode('utf-8'))


def main():
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    print(f'\n🚀 短视频稿生成器已启动')
    print(f'   访问地址: http://localhost:{PORT}')
    print(f'   按 Ctrl+C 停止\n')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n👋 服务已停止')
        server.server_close()


if __name__ == '__main__':
    main()
