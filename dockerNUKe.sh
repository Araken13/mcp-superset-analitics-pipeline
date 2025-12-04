cd ~

cat > docker_nuke.sh << 'SCRIPT_END'
#!/bin/bash

echo "☢️  DESTRUIÇÃO ATÔMICA DO DOCKER ☢️"
echo "===================================="
echo ""
echo "⚠️  ISSO VAI APAGAR TUDO DO DOCKER!"
echo ""
read -p "Digite 'DESTRUIR' para continuar: " confirm

if [ "$confirm" != "DESTRUIR" ]; then
    echo "❌ Cancelado"
    exit 1
fi

echo ""
echo "🔥 INICIANDO..."

docker kill $(docker ps -q) 2>/dev/null || true
docker stop $(docker ps -aq) 2>/dev/null || true
docker rm -f $(docker ps -aq) 2>/dev/null || true
docker rmi -f $(docker images -aq) 2>/dev/null || true
docker volume rm -f $(docker volume ls -q) 2>/dev/null || true
docker network prune -f
docker system prune -a -f --volumes
docker builder prune -a -f

sudo systemctl stop docker
sudo systemctl stop docker.socket
sudo rm -rf /var/lib/docker/containers/* 2>/dev/null || true
sudo rm -rf /var/lib/docker/volumes/* 2>/dev/null || true
sudo systemctl start docker

sleep 5

echo ""
echo "✅ COMPLETO!"
echo ""
docker system df
SCRIPT_END

chmod +x docker_nuke.sh
./docker_nuke.sh
