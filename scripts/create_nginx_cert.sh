#!/bin/bash
# Script to create nginx certificate and write to shared volume

set -e

CERT_SERVICE_URL="${CERT_SERVICE_URL:-http://localhost:8015}"
INTERNAL_TOKEN="${INTERNAL_SERVICE_TOKEN:-internal-service-token-change-in-production}"

echo "Requesting certificate from Cert Service..."
RESPONSE=$(curl -s -X POST "${CERT_SERVICE_URL}/v1/certificates/enroll-service" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${INTERNAL_TOKEN}" \
  -d '{
    "service_id": "nginx",
    "service_type": "nginx",
    "subject_cn": "nginx.sentinelgrid.local",
    "dns_names": ["nginx", "nginx.local", "localhost"],
    "ip_addresses": [],
    "ttl_hours": 8760
  }')

if [ $? -ne 0 ]; then
  echo "Error: Failed to connect to Cert Service at ${CERT_SERVICE_URL}"
  exit 1
fi

# Extract certificate and key using Python
CERT_DATA=$(echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'certificate_pem' in data and 'private_key_pem' in data:
        print('SUCCESS')
        print(data['certificate_pem'])
        print('---KEY---')
        print(data['private_key_pem'])
    else:
        print('ERROR: Missing certificate data')
        print(json.dumps(data, indent=2))
        sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    print('Response:', sys.stdin.read())
    sys.exit(1)
")

if [ $? -ne 0 ] || [ "$(echo "$CERT_DATA" | head -1)" != "SUCCESS" ]; then
  echo "Error: Failed to get certificate from Cert Service"
  echo "Response: $RESPONSE"
  exit 1
fi

# Extract certificate and key
CERT=$(echo "$CERT_DATA" | sed -n '/^SUCCESS$/,/^---KEY---$/p' | sed '1d;$d')
KEY=$(echo "$CERT_DATA" | sed -n '/^---KEY---$/,/^$/p' | sed '1d')

# Write to IAM agent container (which has access to the volume)
echo "Writing certificate to shared volume via IAM agent container..."
docker-compose -f docker-compose.dev.yml exec -T iam_agent sh -c "
  mkdir -p /opt/keycloak/certs
  cat > /opt/keycloak/certs/tls.crt << 'EOF'
$CERT
EOF
  cat > /opt/keycloak/certs/tls.key << 'EOF'
$KEY
EOF
  chmod 644 /opt/keycloak/certs/tls.crt
  chmod 600 /opt/keycloak/certs/tls.key
  ls -la /opt/keycloak/certs/
"

if [ $? -eq 0 ]; then
  echo "✅ Certificate created successfully!"
  echo "Restarting nginx..."
  docker-compose -f docker-compose.dev.yml restart nginx
else
  echo "❌ Failed to write certificate to volume"
  exit 1
fi

