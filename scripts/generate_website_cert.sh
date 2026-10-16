#!/bin/bash
# Generate a self-signed certificate for the website with proper SANs

set -e

CERT_DIR="./infra/nginx/certs"
mkdir -p "$CERT_DIR"

# Generate certificate with proper Subject Alternative Names
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$CERT_DIR/website.key" \
  -out "$CERT_DIR/website.crt" \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1,IP:::1"

# Copy to the location Nginx expects (for website)
cp "$CERT_DIR/website.crt" "$CERT_DIR/tls.crt"
cp "$CERT_DIR/website.key" "$CERT_DIR/tls.key"

echo "Certificate generated at $CERT_DIR/website.crt"
echo "Note: This is a self-signed certificate. For local development, consider using mkcert for browser trust."

