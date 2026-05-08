#!/usr/bin/env bash
# Quick smoke-test of every endpoint via curl.
# Usage: PRINTD_URL=http://localhost:8080 PRINTD_API_KEY=... ./curl.sh sample.png
set -euo pipefail

URL="${PRINTD_URL:-http://localhost:8080}"
KEY="${PRINTD_API_KEY:-changeme}"
IMG="${1:-sample.png}"

H=(-H "Authorization: Bearer ${KEY}")

echo "→ GET /healthz"
curl -sS "${URL}/healthz" | jq .

echo "→ GET /status"
curl -sS "${H[@]}" "${URL}/status" | jq .

echo "→ POST /print/upload (multipart, ${IMG})"
curl -sS -X POST "${H[@]}" -F "image=@${IMG}" -F "cut=true" "${URL}/print/upload" | jq .

echo "→ POST /print (JSON)"
B64=$(base64 -w0 "${IMG}")
curl -sS -X POST "${H[@]}" -H "Content-Type: application/json" \
     -d "{\"image\": \"data:image/png;base64,${B64}\", \"cut\": true}" \
     "${URL}/print" | jq .

echo "→ POST /feed"
curl -sS -X POST "${H[@]}" -H "Content-Type: application/json" \
     -d '{"lines": 2}' "${URL}/feed" | jq .

echo "→ POST /cut"
curl -sS -X POST "${H[@]}" -H "Content-Type: application/json" \
     -d '{"partial": false}' "${URL}/cut" | jq .
