#!/bin/bash
# NexusOS TLS Setup with Let's Encrypt
# Run as: sudo bash setup-tls.sh

set -e

DOMAIN="${1:-nexusos.ai}"
EMAIL="${2:-admin@${DOMAIN}}"
NGINX_CONTAINER="nexusos-nginx"

echo "🔐 Setting up Let's Encrypt TLS for $DOMAIN"

# Install certbot
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    apt-get update -qq
    apt-get install -y -qq certbot python3-certbot-nginx
fi

# Stop any existing nginx
docker rm -f $NGINX_CONTAINER 2>/dev/null || true

# Create nginx config for Let's Encrypt challenges
cat > /tmp/nginx-le.conf << 'EOF'
events {
    worker_connections 1024;
}
http {
    server {
        listen 80;
        server_name _;
        
        location /.well-known/acme-challenge/ {
            root /var/www/html;
        }
        
        location / {
            proxy_pass http://127.0.0.1:8080;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

# Start temp nginx for challenges
docker run -d --name $NGINX_CONTAINER \
    -p 80:80 \
    -v /tmp/nginx-le.conf:/etc/nginx/nginx.conf:ro \
    nginx:latest

sleep 2

# Get certificate
echo "Getting certificate for $DOMAIN..."
certbot certonly --nginx -d $DOMAIN --non-interactive --agree-tos --email $EMAIL || {
    echo "Trying standalone mode..."
    certbot certonly --standalone -d $DOMAIN --non-interactive --agree-tos --email $EMAIL
}

# Create production nginx config with TLS
cat > /tmp/nginx-https.conf << EOF
events {
    worker_connections 1024;
}
http {
    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name $DOMAIN;
        return 301 https://\$host\$request_uri;
    }
    
    server {
        listen 443 ssl http2;
        server_name $DOMAIN;
        
        ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
        
        location /.well-known/acme-challenge/ {
            root /var/www/html;
        }
        
        location / {
            proxy_pass http://127.0.0.1:8080;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
        }
    }
}
EOF

# Restart nginx with HTTPS
docker rm -f $NGINX_CONTAINER
docker run -d --name $NGINX_CONTAINER \
    -p 80:80 \
    -p 443:443 \
    -v /tmp/nginx-https.conf:/etc/nginx/nginx.conf:ro \
    -v /etc/letsencrypt:/etc/letsencrypt:ro \
    -v /var/www/html:/var/www/html:ro \
    nginx:latest

# Setup auto-renewal
(crontab -l 2>/dev/null | grep -v certbot; echo "0 3 * * * certbot renew --quiet --deploy-hook 'docker exec $NGINX_CONTAINER nginx -s reload'") | crontab -

echo "✅ TLS setup complete!"
echo "   Domain: $DOMAIN"
echo "   HTTPS: https://$DOMAIN"
echo "   Auto-renewal: enabled (3AM daily)"
