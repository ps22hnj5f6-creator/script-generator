# 短视频引流稿生成器 Docker 镜像
FROM node:22-alpine
WORKDIR /app
COPY package.json server.js 短视频稿生成器.html ./
EXPOSE 3000
ENV PORT=3000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/',r=>process.exit(r.statusCode===200?0:1))"
CMD ["node", "server.js"]
