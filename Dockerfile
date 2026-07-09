# 短视频引流稿生成器 Docker 镜像
FROM node:22-alpine
WORKDIR /app
COPY package.json server.js 短视频稿生成器.html ./
EXPOSE 3000
ENV PORT=3000
CMD ["node", "server.js"]
