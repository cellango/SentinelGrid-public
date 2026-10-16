# Keycloak Certificate Setup with Cert Service

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Overview

This document describes how Keycloak is configured to use certificates from the Cert Service for HTTPS/TLS encryption, replacing the insecure `sslRequired: "none"` setting.

## Architecture

1. **Cert Service Integration**: The IAM Agent's Keycloak seeder requests a certificate from the Cert Service during initialization
2. **Certificate Storage**: Certificates are written to a shared Docker volume (`keycloak_certs`)
3. **Nginx Reverse Proxy**: A shared nginx service (`nginx`) sits in front of Keycloak (and can be extended for other services) to:
   - Redirect all HTTP traffic to HTTPS
   - Terminate SSL/TLS using certificates from Cert Service
   - Proxy HTTPS requests to Keycloak (running HTTP internally)
   - Provide a centralized reverse proxy for all SentinelGrid services
4. **Keycloak Configuration**: Keycloak runs HTTP-only internally, with nginx handling HTTPS termination

## Implementation Details

### 1. Certificate Request Flow

The `KeycloakSeeder.request_keycloak_certificate()` method:
- Requests a certificate from the Cert Service API (`/v1/certificates/enroll-service`)
- Writes the certificate, private key, and CA chain to `/opt/keycloak/certs/`:
  - `tls.crt` - Server certificate (644 permissions)
  - `tls.key` - Private key (600 permissions)
  - `ca-chain.crt` - CA certificate chain (644 permissions)

### 2. Docker Volume Configuration

**Shared Volume**: `keycloak_certs`
- **IAM Agent**: Mounts volume with read-write access to write certificates
- **Keycloak**: Mounts volume with read-only access to read certificates

```yaml
volumes:
  keycloak_certs:  # Shared volume for certificates
```

### 3. Nginx Reverse Proxy Configuration

A shared nginx container (`nginx`) sits in front of Keycloak:
- **HTTP Port 8081**: Redirects all traffic to HTTPS (port 8443)
- **HTTPS Port 8443**: Terminates SSL/TLS and proxies to Keycloak
- **Certificate Files**: Mounted from `keycloak_certs` volume
- **Keycloak Backend**: Proxies to `keycloak:8080` (internal HTTP)

### 4. Keycloak Internal Configuration

Keycloak runs in production mode (`start`) but HTTP-only internally:
- **Internal HTTP Port**: 8080 (not exposed externally)
- **Proxy Mode**: Configured with `KC_PROXY=edge` for proper header handling
- **No Direct HTTPS**: HTTPS is handled by nginx reverse proxy

### 5. Realm SSL Configuration

The `sentinelgrid` realm is configured with:
- `sslRequired: "external"` - Requires SSL for external connections
- This ensures secure communication while allowing internal HTTP if needed

## Service Dependencies

The certificate request requires:
1. **Cert Service** must be running
2. **Step-CA** must be running (CA backend)
3. **IAM Agent** must have access to:
   - `CERT_SERVICE_URL` environment variable
   - `INTERNAL_SERVICE_TOKEN` for authentication
   - `KEYCLOAK_CERT_DIR` for certificate storage path

## Startup Sequence

1. **Step-CA** starts and initializes the CA
2. **Cert Service** starts and connects to Step-CA
3. **Keycloak** starts (HTTP-only, internal)
4. **IAM Agent** starts and runs Keycloak seeder:
   - Seeds realm, clients, roles, users
   - **Requests certificate from Cert Service**
   - **Writes certificate files to shared volume**
   - Disables default admin user
5. **Nginx** starts:
   - Reads certificates from shared volume
   - Enables HTTPS on port 8443
   - Redirects HTTP (port 8081) to HTTPS
   - Proxies requests to Keycloak

**Note**: If certificates don't exist when nginx starts, it will fail. Restart nginx after certificates are created: `docker-compose restart nginx`

## Certificate Details

- **Subject CN**: `keycloak.sentinelgrid.local`
- **DNS Names**: `keycloak`, `keycloak.local`, `localhost`
- **TTL**: 8760 hours (1 year)
- **Service Type**: `keycloak`

## Security Considerations

1. **Private Key Permissions**: Set to 600 (owner read/write only)
2. **Certificate Permissions**: Set to 644 (readable by all, writable by owner)
3. **Volume Access**: Keycloak has read-only access to prevent accidental modification
4. **Default Admin Disabled**: The default Keycloak admin user is automatically disabled

## Troubleshooting

### Certificates Not Found
If nginx starts before certificates are created:
- Nginx will fail to start (certificate files missing)
- After certificates are created, restart nginx: `docker-compose restart nginx`
- Nginx will then enable HTTPS and redirect HTTP to HTTPS

### Certificate Request Fails
- Check Cert Service logs: `docker-compose logs cert_service`
- Check Step-CA logs: `docker-compose logs step-ca`
- Verify `INTERNAL_SERVICE_TOKEN` matches in both services
- Verify Cert Service is healthy: `curl http://localhost:8015/health`

### Keycloak HTTPS Not Working
- Verify certificate files exist: `docker-compose exec nginx ls -la /etc/nginx/certs/`
- Check nginx logs: `docker-compose logs nginx`
- Check Keycloak logs: `docker-compose logs keycloak`
- Verify nginx configuration: `docker-compose exec nginx nginx -t`
- Test HTTP redirect: `curl -I http://localhost:8081` (should return 301 redirect)
- Test HTTPS: `curl -k https://localhost:8443/health/ready`

## Manual Certificate Verification

```bash
# Check if certificates exist in volume (from IAM Agent)
docker-compose exec iam_agent ls -la /opt/keycloak/certs/

# Check if certificates are accessible to nginx
docker-compose exec nginx ls -la /etc/nginx/certs/

# View certificate details
docker-compose exec nginx openssl x509 -in /etc/nginx/certs/tls.crt -text -noout

# Test HTTP redirect (should return 301)
curl -I http://localhost:8081

# Test HTTPS connection
curl -k https://localhost:8443/health/ready

# Test HTTPS with Keycloak endpoint
curl -k https://localhost:8443/realms/sentinelgrid/.well-known/openid-configuration
```

## Future Enhancements

1. **Automatic Keycloak Restart**: After certificate creation, automatically restart Keycloak
2. **Certificate Renewal**: Set up automatic renewal before expiration
3. **Certificate Monitoring**: Alert when certificates are expiring soon
4. **Multiple Certificates**: Support for multiple domains/certificates

