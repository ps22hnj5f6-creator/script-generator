# 短视频稿生成器 Docker 镜像（Python 服务器，零额外依赖）
FROM python:3.11-slim
WORKDIR /app

# 复制运行所需文件
COPY server.py fetch_hotlist.py 短视频稿生成器.html hotlist.json ./

EXPOSE 3000
ENV PORT=3000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:3000/')" || exit 1

CMD ["python3", "server.py"]
