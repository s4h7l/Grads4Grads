#!/usr/bin/env sh
cd "$(dirname "$0")/site" || exit 1
echo "Grads4Grads at http://127.0.0.1:8000/index.html"
python3 -m http.server 8000 --bind 127.0.0.1
