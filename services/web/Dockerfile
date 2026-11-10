# Stage 1: Build Next.js static export
FROM node:20-alpine AS builder

WORKDIR /build

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Serve with unprivileged non-root Nginx
FROM nginx:alpine AS runner

RUN apk add --no-cache curl && \
    addgroup -g 10001 -S appuser && \
    adduser -u 10001 -S appuser -G appuser && \
    mkdir -p /tmp/client_temp /tmp/proxy_temp_path /tmp/fastcgi_temp /tmp/uwsgi_temp /tmp/scgi_temp && \
    chown -R appuser:appuser /tmp /var/cache/nginx /var/run /var/log/nginx

COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=builder --chown=appuser:appuser /build/out /usr/share/nginx/html

USER 10001

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD curl -f http://localhost:8080/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
