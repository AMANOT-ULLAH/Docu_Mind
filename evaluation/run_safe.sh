#!/bin/bash
# ব্যবহার: ./run_safe.sh <মডেল-তালিকা> <নাম>
cd "$(dirname "$0")"
if pgrep -f "[r]un_eval.py" > /dev/null; then
  echo "আরেকটা run_eval এখনো চলছে, থামলাম।"; exit 1
fi
GEMINI_MODELS="$1" nohup python run_eval.py > "results/run_$2.txt" 2>&1 &
echo "শুরু হলো: $2 (pid $!)"