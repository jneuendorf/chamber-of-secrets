# Build stage
FROM oven/bun:1-alpine AS builder
WORKDIR /app

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .

# Bake the API base path into the bundle so the browser calls /api/...
# nginx in the serve stage proxies those requests to the backend container.
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=$VITE_API_BASE

RUN bun run build

# Serve stage — nginx:alpine is ~8 MB
FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# openssl generates self-signed fallback certs at startup (via the entrypoint script below).
RUN apk add --no-cache openssl

# Runs before nginx starts; copies real certs if mounted, else generates self-signed fallback.
COPY 40-setup-certs.sh /docker-entrypoint.d/40-setup-certs.sh
RUN chmod +x /docker-entrypoint.d/40-setup-certs.sh

EXPOSE 80 443
