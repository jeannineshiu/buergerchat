# Build context is frontend/ (Railway service root directory = frontend).
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# NEXT_PUBLIC_* is inlined into the client bundle at build time, so it must
# arrive as a build arg (Railway passes service variables to Dockerfile ARGs).
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

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
