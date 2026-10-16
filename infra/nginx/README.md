# SentinelGrid Nginx Reverse Proxy

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


## Overview

This is a shared nginx reverse proxy service for all SentinelGrid services. It provides:

- **SSL/TLS Termination**: Handles HTTPS for services that need it
- **HTTP to HTTPS Redirect**: Automatically redirects insecure HTTP to secure HTTPS
- **Load Balancing**: Can distribute traffic across multiple service instances
- **Centralized Configuration**: Single point of configuration for routing and security headers

## Current Configuration

### Keycloak Integration

- **HTTP Port 8081**: Redirects all traffic to HTTPS (port 8443)
- **HTTPS Port 8443**: Terminates SSL and proxies to Keycloak (internal HTTP on port 8080)
- **Certificates**: Mounted from `keycloak_certs` volume

## Architecture

```
External Request (HTTP)  → nginx:8081 → Redirect 301 → nginx:8443 (HTTPS) → keycloak:8080 (HTTP)
External Request (HTTPS) → nginx:8443 (HTTPS) → keycloak:8080 (HTTP)
Internal Service         → keycloak:8080 (HTTP) [direct, bypasses nginx]
```

## Adding New Services

To add a new service to nginx:

1. **Add server block** in `infra/nginx/nginx.conf`:
   ```nginx
   server {
       listen 8444 ssl http2;
       server_name _;
       
       ssl_certificate /etc/nginx/certs/service-tls.crt;
       ssl_certificate_key /etc/nginx/certs/service-tls.key;
       
       location / {
           proxy_pass http://service_name:8000;
           # ... proxy settings ...
       }
   }
   ```

2. **Add port mapping** in `docker-compose.dev.yml`:
   ```yaml
   nginx:
     ports:
       - "8444:8444"  # HTTPS for new service
   ```

3. **Mount certificates** (if different from Keycloak):
   ```yaml
   nginx:
     volumes:
       - service_certs:/etc/nginx/certs/service:ro
   ```

## Security Features

- **HSTS**: Strict Transport Security headers
- **Security Headers**: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection
- **Modern TLS**: TLS 1.2 and 1.3 only
- **Strong Ciphers**: High-grade cipher suites

## Health Checks

Nginx health check endpoint: `http://nginx:8080/health` (proxies to Keycloak)

## Troubleshooting

```bash
# Check nginx configuration
docker-compose exec nginx nginx -t

# View nginx logs
docker-compose logs nginx

# Reload nginx configuration (without restart)
docker-compose exec nginx nginx -s reload

# Test HTTP redirect
curl -I http://localhost:8081

# Test HTTPS
curl -k https://localhost:8443/health/ready
```

## Future Enhancements

- **Rate Limiting**: Add rate limiting per service
- **Authentication**: Add authentication layer for internal services
- **Monitoring**: Add Prometheus metrics endpoint
- **Logging**: Centralized access logs
- **Caching**: Response caching for static content
- **Compression**: Gzip compression for responses

