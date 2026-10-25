#!/bin/sh
set -eu
if ! docker info >/dev/null 2>&1; then
  mkdir -p /var/lib/docker /var/log
  nohup dockerd --data-root=/var/lib/docker --host=unix:///var/run/docker.sock > /var/log/bmdl-docker.log 2>&1 < /dev/null &
fi
for n in $(seq 1 40); do
  if docker info >/dev/null 2>&1; then docker version --format '{{.Server.Version}}'; exit 0; fi
  sleep 1
done
tail -n 40 /var/log/bmdl-docker.log
exit 1
