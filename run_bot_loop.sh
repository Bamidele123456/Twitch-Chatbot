#!/bin/bash

while true; do
  echo "Starting Twitch bot at $(date)"
  source myenv/bin/activate
  python3 app.py
  echo "Bot exited at $(date). Restarting in 5 seconds..."
  sleep 5
done
