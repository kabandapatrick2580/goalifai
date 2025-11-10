#!/usr/bin/env bash
gunicorn -k gevent --worker-connections 1000 -w 2 -b 0.0.0.0:8000 app:app
