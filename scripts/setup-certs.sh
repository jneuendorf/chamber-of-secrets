#!/usr/bin/env bash
# Generates a locally-trusted TLS certificate for the Raspberry Pi using mkcert.
# Run this once on your development machine, then copy the certs/ folder to the Pi.
#
# Prerequisites (install once per machine):
#   macOS:   brew install mkcert
#   Linux:   https://github.com/FiloSottile/mkcert#linux
#   Windows: choco install mkcert
#
# On each mobile device that needs to trust the certificate:
#   iOS:     Settings → General → VPN & Device Management → install the CA profile,
#            then Settings → General → About → Certificate Trust Settings → enable it.
#   Android: Settings → Security → Install from storage → pick rootCA.pem.

set -euo pipefail

CERTS_DIR="$(cd "$(dirname "$0")/.." && pwd)/certs"
mkdir -p "$CERTS_DIR"

# Install the local CA into the system trust store (run once per machine).
mkcert -install

# Detect the Pi's local IP so the cert covers it.
# Override by passing the hostname/IP as arguments:  ./setup-certs.sh mypi.local 192.168.1.50
if [ "$#" -gt 0 ]; then
    HOSTS=("$@")
else
    # Attempt to auto-detect; falls back to localhost only.
    LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo "")
    HOSTS=(localhost 127.0.0.1)
    if [ -n "$LOCAL_IP" ]; then
        HOSTS+=("$LOCAL_IP")
    fi
    echo "Detected hosts: ${HOSTS[*]}"
    echo "Tip: pass custom hostnames/IPs as arguments — e.g. ./setup-certs.sh pi.local 192.168.1.50"
fi

mkcert \
    -cert-file "$CERTS_DIR/cert.pem" \
    -key-file  "$CERTS_DIR/key.pem" \
    "${HOSTS[@]}"

echo ""
echo "✓ Certificate written to $CERTS_DIR"
echo ""
echo "To trust this certificate on mobile devices, copy the root CA to the device:"
echo "  $(mkcert -CAROOT)/rootCA.pem"
