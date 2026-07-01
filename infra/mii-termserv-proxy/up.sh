#!/usr/bin/env bash
# Launch the mTLS proxy to the MII SU-TermServ Ontoserver on the matchbox docker network,
# then smoke-test that it reaches the Ontoserver through the client certificate.
# Prereq: certs/client.crt (full chain) + certs/client.key (RSA, unencrypted PEM) in place.
set -euo pipefail
cd "$(dirname "$0")"
NET="${MB_NETWORK:-genomdefhirmapper_default}"   # matchbox's docker network
NAME=mii-termserv-proxy

[ -f certs/client.crt ] && [ -f certs/client.key ] || {
  echo "ERROR: put your SU-TermServ cert at certs/client.crt (full chain) and key at certs/client.key" >&2
  echo "       request one via support-medic@uni-koeln.de — see README.md" >&2; exit 2; }

docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" --network "$NET" --restart unless-stopped \
  -v "$PWD/nginx.conf:/etc/nginx/nginx.conf:ro" \
  -v "$PWD/certs:/certs:ro" \
  nginx:1.27-alpine >/dev/null
echo "started $NAME on network $NET"

echo "smoke test (from inside the network): CodeSystem count via mTLS ..."
sleep 2
docker run --rm --network "$NET" curlimages/curl:latest -s --max-time 30 \
  "http://$NAME/fhir/CodeSystem?_summary=count" | head -c 400
echo
echo "If you see a FHIR Bundle above (not an SSL/HTML error), mTLS works."
echo "Next: set matchbox txServer -> http://$NAME/fhir and restart matchbox (see README.md)."
