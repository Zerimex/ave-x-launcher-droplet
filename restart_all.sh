#!/bin/bash
LOCAL_IP=$(docker inspect ave-local-server --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
echo "local-server IP: $LOCAL_IP"

docker stop ave-rain ave-promocode 2>/dev/null
docker rm ave-rain ave-promocode 2>/dev/null

docker run -d --name ave-rain --restart unless-stopped \
  --network ave-x-net --add-host="local-server:$LOCAL_IP" \
  -v /root/ave-x-launcher/assets/userdata:/app/assets/userdata \
  -v /root/ave-x-launcher/userconfig.txt:/app/userconfig.txt \
  -e DISPLAY=:99 -e PYTHONUNBUFFERED=1 -e PYTHONPATH=/app \
  -e MODULE=rain -e DOCKER_SOCKET_HOST=local-server \
  -e RAIN_BYPASS=camoufox_solver -e RAIN_SOLVER=2captcha -e RAIN_SITE=HarvesterGG \
  ave-x-launcher python launcher.py

docker run -d --name ave-promocode --restart unless-stopped \
  --network ave-x-net --add-host="local-server:$LOCAL_IP" \
  -v /root/ave-x-launcher/assets/userdata:/app/assets/userdata \
  -v /root/ave-x-launcher/userconfig.txt:/app/userconfig.txt \
  -e DISPLAY=:99 -e PYTHONUNBUFFERED=1 -e PYTHONPATH=/app \
  -e MODULE=promocode -e DOCKER_SOCKET_HOST=local-server \
  -e PROMOCODE_BYPASS=none -e PROMOCODE_SITE=MM2WILD \
  ave-x-launcher python launcher.py

echo "DONE"
