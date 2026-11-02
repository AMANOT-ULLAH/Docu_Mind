#!/bin/bash
# একটা ফাইল upload করে তার progress DB থেকে দেখায়। ব্যবহার: bash watch_progress.sh <ফাইল>
FILE="${1:-$HOME/docuMind/evaluation/dataset_big/scanned_30.pdf}"
ID=$(curl -s -F "files=@$FILE" http://127.0.0.1:8000/documents | python3 -c "import sys,json; print(json.load(sys.stdin)['documents'][0]['id'])")
echo "document id: $ID"
for i in $(seq 1 40); do
  ROW=$(docker exec documind-db psql -U documind -d documind -tAc "SELECT status, pages_done, pages_total FROM documents WHERE id=$ID")
  echo "$(date +%T)  $ROW"
  case "$ROW" in done*|failed*) break;; esac
  sleep 3
done
