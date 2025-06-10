# 使用官方 Node.js 映像檔
FROM node:18-alpine AS base

# 1. 安裝依賴
FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

# 2. 建置
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# 3. 運行
FROM base AS runner
WORKDIR /app
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000
CMD ["npm", "start"] 