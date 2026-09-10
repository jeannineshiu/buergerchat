# Build context is frontend/ (Railway service root directory = frontend).
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# No build-time API URL: the browser calls the same-origin /api proxy, and
# the proxy reads BACKEND_URL at runtime (src/lib/proxy.ts).
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production
# The standalone server binds localhost unless told otherwise; PORT comes
# from Railway at runtime and server.js picks it up itself.
ENV HOSTNAME=0.0.0.0

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]
