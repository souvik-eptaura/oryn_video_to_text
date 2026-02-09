FROM nginx:1.25-alpine

RUN apk add --no-cache openssl \
    && mkdir -p /etc/nginx/sites-enabled /etc/ssl/private \
    && openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -subj "/CN=localhost" \
        -keyout /etc/ssl/private/ssl-cert-snakeoil.key \
        -out /etc/ssl/certs/ssl-cert-snakeoil.pem

COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY docker/nginx/sites-enabled/default.conf /etc/nginx/sites-enabled/default.conf
