#!/bin/bash
cd "$(dirname "$0")" || exit 1
source ../.venv/bin/activate
docker start documind-db > /dev/null 2>&1 && echo "database চালু"
sleep 3
uvicorn app.main:app --reload
