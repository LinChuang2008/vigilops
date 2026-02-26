#!/bin/bash
# Generate self-signed SSL certificate for development
# Usage: bash scripts/generate-self-signed-cert.sh [domain]

set -e

DOMAIN="${1:-localhost}"
CERT_DIR="nginx/certs"

mkdir -p "$CERT_DIR"

echo "🔐 Generating self-signed certificate for: $DOMAIN"

openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout "$CERT_DIR/privkey.pem" \
  -out "$CERT_DIR/fullchain.pem" \
  -subj "/CN=$DOMAIN" \
  -addext "subjectAltName=DNS:$DOMAIN,DNS:www.$DOMAIN,IP:127.0.0.1"

echo "✅ Certificate generated in $CERT_DIR/"
echo "   - fullchain.pem (certificate)"
echo "   - privkey.pem   (private key)"
echo ""
echo "⚠️  Self-signed certs will show browser warnings. For production, use Let's Encrypt."
echo ""
echo "Start with HTTPS:"
echo "  docker compose -f docker-compose.yml -f docker-compose.ssl.yml up -d"
