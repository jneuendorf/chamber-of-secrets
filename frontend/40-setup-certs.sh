#!/bin/sh
# Runs via nginx's /docker-entrypoint.d/ mechanism before nginx starts.
# Copies mkcert certs if mounted, otherwise generates a self-signed fallback.
set -e

mkdir -p /etc/nginx/ssl

if [ -f /etc/nginx/certs/cert.pem ] && [ -f /etc/nginx/certs/key.pem ]; then
    cp /etc/nginx/certs/cert.pem /etc/nginx/ssl/cert.pem
    cp /etc/nginx/certs/key.pem  /etc/nginx/ssl/key.pem
    echo "40-setup-certs: using mounted mkcert certificates"
else
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/key.pem \
        -out    /etc/nginx/ssl/cert.pem \
        -subj   "/CN=localhost" 2>/dev/null
    echo "40-setup-certs: no certs mounted — generated self-signed fallback"
fi
