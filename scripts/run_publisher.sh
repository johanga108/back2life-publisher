#!/bin/zsh
set -u

cd "/Users/johanga/Documents/Back to LIfe" || exit 1

mkdir -p logs state

lockdir="state/publisher.lock"
if ! mkdir "$lockdir" 2>/dev/null; then
  echo "$(date '+%Y-%m-%d %H:%M:%S %Z') publisher already running"
  exit 0
fi
trap 'rmdir "$lockdir"' EXIT

exit_code=1
for attempt in 1 2 3; do
  echo "$(date '+%Y-%m-%d %H:%M:%S %Z') publisher attempt $attempt"
  /usr/bin/python3 scripts/publish_next.py
  exit_code=$?
  if [ "$exit_code" -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S %Z') publisher succeeded"
    exit 0
  fi
  echo "$(date '+%Y-%m-%d %H:%M:%S %Z') publisher failed with status $exit_code"
  if [ "$attempt" -lt 3 ]; then
    sleep 120
  fi
done

exit "$exit_code"
