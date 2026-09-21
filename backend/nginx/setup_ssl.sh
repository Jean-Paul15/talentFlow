# Script d'installation SSL - Let's Encrypt
#!/bin/bash

set -e

echo "🔒 Installation Let's Encrypt pour TalentFlow"
echo ""

# Variables
DOMAIN="talentflow.tg"
EMAIL="admin@talentflow.tg"

# Installation Certbot
echo "📦 Installation Certbot..."
apt-get update
apt-get install -y certbot python3-certbot-nginx

# Obtenir certificat
echo "📜 Obtention certificat SSL..."
certbot --nginx \
  --non-interactive \
  --agree-tos \
  --email $EMAIL \
  -d $DOMAIN \
  -d www.$DOMAIN \
  -d monitoring.$DOMAIN

# Auto-renouvellement
echo "🔄 Configuration auto-renouvellement..."
systemctl enable certbot.timer
systemctl start certbot.timer

# Test configuration Nginx
echo "✅ Test configuration Nginx..."
nginx -t

# Reload Nginx
echo "🔄 Reload Nginx..."
systemctl reload nginx

echo ""
echo "✅ SSL configuré avec succès!"
echo "Certificats expiration: 90 jours (auto-renouvellement activé)"
