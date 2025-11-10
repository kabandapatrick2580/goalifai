#!/usr/bin/env bash
nohup gunicorn -k gevent --worker-connections 1000 -w 2 -b 0.0.0.0:8000 app:app > gunicorn.log 2>&1 &
echo "Gunicorn started in background (check gunicorn.log for logs)"
