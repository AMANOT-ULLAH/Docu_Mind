#!/bin/bash
FILE="${1:-$HOME/docuMind/evaluation/dataset_big/scanned_30.pdf}"
ID=$(curl -s -F "files=@$FILE" http://127.0.0.1:8000/documents | python3 -c "import sys,json; print(json.load(sys.stdin)['documents'][0]['id'])")
echo "document id: $ID"
for i in $(seq 1 60); do
  R=$(curl -s http://127.0.0.1:8000/documents/$ID | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'], d['stage'], d['pages_done'], '/', d['pages_total'])")
  echo "$(date +%T)  $R"
  case "$R" in done*|failed*) break;; esac
  sleep 3
done
