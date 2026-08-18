#!/bin/bash
set -e

NETWORK="ave-x-net"
IMAGE="ave-x-launcher:latest"

# Clean old
docker stop ave-rain ave-promocode ave-local-server 2>/dev/null || true
docker rm ave-rain ave-promocode ave-local-server 2>/dev/null || true
docker network rm $NETWORK 2>/dev/null || true

# Create network
docker network create $NETWORK

# Start local-server first
docker run -d --name ave-local-server --restart unless-stopped \
  --network $NETWORK \
  -v /root/ave-x-launcher/assets/userdata:/app/assets/userdata \
  -v /root/ave-x-launcher/userconfig.txt:/app/userconfig.txt \
  -e DISPLAY=:99 -e PYTHONUNBUFFERED=1 -e PYTHONPATH=/app \
  -e MODULE=local-server \
  $IMAGE python launcher.py

echo "Waiting for local-server to start..."
sleep 5

# Get local-server IP
LOCAL_IP=$(docker inspect ave-local-server --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
echo "local-server IP: $LOCAL_IP"

# Start rain with --add-host for DNS workaround
docker run -d --name ave-rain --restart unless-stopped \
  --network $NETWORK --add-host="local-server:$LOCAL_IP" \
  -v /root/ave-x-launcher/assets/userdata:/app/assets/userdata \
  -v /root/ave-x-launcher/userconfig.txt:/app/userconfig.txt \
  -e DISPLAY=:99 -e PYTHONUNBUFFERED=1 -e PYTHONPATH=/app \
  -e MODULE=rain -e DOCKER_SOCKET_HOST=local-server \
  -e RAIN_BYPASS=camoufox_solver -e RAIN_SOLVER=2captcha -e RAIN_SITE=HarvesterGG \
  $IMAGE python launcher.py

# Start promocode with --add-host for DNS workaround
docker run -d --name ave-promocode --restart unless-stopped \
  --network $NETWORK --add-host="local-server:$LOCAL_IP" \
  -v /root/ave-x-launcher/assets/userdata:/app/assets/userdata \
  -v /root/ave-x-launcher/userconfig.txt:/app/userconfig.txt \
  -e DISPLAY=:99 -e PYTHONUNBUFFERED=1 -e PYTHONPATH=/app \
  -e MODULE=promocode -e DOCKER_SOCKET_HOST=local-server \
  -e PROMOCODE_BYPASS=none -e PROMOCODE_SITE=MM2WILD \
  $IMAGE python launcher.py

echo "=== All containers started ==="
docker ps --format 'table {{.Names}}\t{{.Status}}'
