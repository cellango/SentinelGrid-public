# Install deps and build
FROM node:20-alpine AS builder

WORKDIR /app

ENV NPM_CONFIG_FETCH_RETRIES=5 \
    NPM_CONFIG_FETCH_RETRY_MINTIMEOUT=20000 \
    NPM_CONFIG_FETCH_RETRY_MAXTIMEOUT=120000 \
    NPM_CONFIG_FETCH_TIMEOUT=120000

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Ensure public directory exists (Next.js may need it)
RUN mkdir -p public

# Provide catalog placeholders for build-time export; runtime mounts real cfg/
RUN mkdir -p cfg/detections cfg/playbooks && \
    echo "{}" > cfg/detections/catalog.yaml && \
    echo "{}" > cfg/playbooks/catalog.yaml

# Build arguments for Next.js environment variables
# These must be available at build time for client-side code
ARG NEXT_PUBLIC_API_URL=http://localhost:8082
ARG NEXT_PUBLIC_API_BASE=http://localhost:8082
ARG NEXT_PUBLIC_IAM_AGENT_URL=http://iam_agent:8000
ARG NEXT_PUBLIC_FORCE_HTTPS=true
ARG NEXT_PUBLIC_HTTPS_PORT=3443

# Set environment variables for build
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE}
ENV NEXT_PUBLIC_IAM_AGENT_URL=${NEXT_PUBLIC_IAM_AGENT_URL}
ENV NEXT_PUBLIC_FORCE_HTTPS=${NEXT_PUBLIC_FORCE_HTTPS}
ENV NEXT_PUBLIC_HTTPS_PORT=${NEXT_PUBLIC_HTTPS_PORT}

# Build the application
RUN npm run build

# Production image with nginx
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3001
ENV HOSTNAME="0.0.0.0"
ENV HOME=/tmp

# Install nginx and patch base packages in the final runtime image.
RUN apk upgrade --no-cache && apk add --no-cache nginx

# Create directories for nginx
RUN mkdir -p /etc/nginx/conf.d /etc/nginx/certs

# Create a non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy the standalone runtime bundle and static assets.
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Copy public directory (Next.js static assets)
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

# The runtime image only needs `node`; remove npm/npx to shrink scan surface.
RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/bin/npm /usr/local/bin/npx

# Copy nginx configuration
# Create main nginx.conf
RUN echo 'events {' > /etc/nginx/nginx.conf && \
    echo '    worker_connections 1024;' >> /etc/nginx/nginx.conf && \
    echo '}' >> /etc/nginx/nginx.conf && \
    echo '' >> /etc/nginx/nginx.conf && \
    echo 'pid /tmp/nginx.pid;' >> /etc/nginx/nginx.conf && \
    echo 'error_log /dev/stderr warn;' >> /etc/nginx/nginx.conf && \
    echo '' >> /etc/nginx/nginx.conf && \
    echo 'http {' >> /etc/nginx/nginx.conf && \
    echo '    access_log /dev/stdout;' >> /etc/nginx/nginx.conf && \
    echo '    client_body_temp_path /tmp/client_temp;' >> /etc/nginx/nginx.conf && \
    echo '    proxy_temp_path /tmp/proxy_temp;' >> /etc/nginx/nginx.conf && \
    echo '    fastcgi_temp_path /tmp/fastcgi_temp;' >> /etc/nginx/nginx.conf && \
    echo '    uwsgi_temp_path /tmp/uwsgi_temp;' >> /etc/nginx/nginx.conf && \
    echo '    scgi_temp_path /tmp/scgi_temp;' >> /etc/nginx/nginx.conf && \
    echo '    include /etc/nginx/conf.d/*.conf;' >> /etc/nginx/nginx.conf && \
    echo '}' >> /etc/nginx/nginx.conf

COPY --chown=root:root nginx.conf /etc/nginx/conf.d/default.conf

# SSL certificates will be mounted as volume in docker-compose
# Create placeholder files so nginx doesn't fail if certs don't exist yet
RUN echo "# Placeholder - replace with actual certs" > /etc/nginx/certs/tls.crt && \
    echo "# Placeholder - replace with actual certs" > /etc/nginx/certs/tls.key && \
    chmod 644 /etc/nginx/certs/tls.crt /etc/nginx/certs/tls.key

RUN chown -R nextjs:nodejs /app

# Expose ports
EXPOSE 3443

# Create startup script that runs both nginx and Next.js
RUN echo '#!/bin/sh' > /app/start.sh && \
    echo 'set -e' >> /app/start.sh && \
    echo 'mkdir -p /tmp/client_temp /tmp/proxy_temp /tmp/fastcgi_temp /tmp/uwsgi_temp /tmp/scgi_temp' >> /app/start.sh && \
    echo 'echo "Starting nginx..."' >> /app/start.sh && \
    echo 'nginx' >> /app/start.sh && \
    echo 'echo "Waiting for nginx to start..."' >> /app/start.sh && \
    echo 'sleep 2' >> /app/start.sh && \
    echo 'echo "Starting Next.js..."' >> /app/start.sh && \
    echo 'exec node server.js' >> /app/start.sh && \
    chmod +x /app/start.sh

USER nextjs:nodejs

# Start nginx and Next.js
CMD ["/app/start.sh"]
