#!/bin/bash
# Initialize Let's Encrypt certificates for production
# Usage: bash scripts/init-letsencrypt.sh <domain> <email>
#
# Prerequisites:
#   - Domain DNS points to this server
#   - Ports 80/443 are open

set -e

DOMAIN="${1:?Usage: $0 <domain> <email>}"
EMAIL="${2:?Usage: $0 <domain> <email>}"
CERT_DIR="${SSL_CERT_DIR:-./nginx/certs}"
CERTBOT_DIR="${CERTBOT_WEBROOT:-./nginx/certbot}"

mkdir -p "$CERT_DIR" "$CERTBOT_DIR"

echo "🔐 Requesting Let's Encrypt certificate for: $DOMAIN"
echo "   Email: $EMAIL"
echo ""

# Step 1: Generate temporary self-signed cert so nginx can start
if [ ! -f "$CERT_DIR/fullchain.pem" ]; then
    echo "📝 Creating temporary self-signed cert for initial nginx startup..."
    openssl req -x509 -nodes -days 1 -newkey rsa:2048 \
        -keyout "$CERT_DIR/privkey.pem" \
        -out "$CERT_DIR/fullchain.pem" \
        -subj "/CN=$DOMAIN" 2>/dev/null
fi

# Step 2: Start nginx
echo "🚀 Starting nginx..."
DOMAIN="$DOMAIN" docker compose -f docker-compose.yml -f docker-compose.ssl.yml up -d nginx-ssl

sleep 3

# Step 3: Request real certificate via certbot
# certbot volume maps SSL_CERT_DIR to /etc/letsencrypt
echo "📜 Requesting certificate from Let's Encrypt..."
docker compose -f docker-compose.yml -f docker-compose.ssl.yml run --rm \
    -e "DOMAIN=$DOMAIN" \
    certbot certonly --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

# Step 4: Symlink certs (certbot stores in live/$DOMAIN/)
# Since certbot volume = SSL_CERT_DIR:/etc/letsencrypt, certs are at $CERT_DIR/live/$DOMAIN/
echo "📁 Linking certificate files..."
ln -sf "live/$DOMAIN/fullchain.pem" "$CERT_DIR/fullchain.pem"
ln -sf "live/$DOMAIN/privkey.pem" "$CERT_DIR/privkey.pem"

# Step 5: Reload nginx
echo "🔄 Reloading nginx..."
docker compose -f docker-compose.yml -f docker-compose.ssl.yml exec nginx-ssl nginx -s reload

echo ""
echo "✅ HTTPS enabled for $DOMAIN"
echo ""
echo "To enable auto-renewal, start with production profile:"
echo "  DOMAIN=$DOMAIN docker compose -f docker-compose.yml -f docker-compose.ssl.yml --profile production up -d"
