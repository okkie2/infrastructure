#!/bin/sh
# Retry only the observed Docker startup failure caused by a missing VPN address.
set -eu
PATH=/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH
state=$(docker inspect --format '{{.State.Status}}|{{.State.Error}}' volition 2>/dev/null) || exit 0
case "$state" in
    'exited|'*'100.126.55.95:8766: bind: cannot assign requested address'*) ;;
    *) exit 0 ;;
esac
# Do not retry until the exact private address is present on its interface.
ip -4 addr show dev tailscale0 | grep -q 'inet 100\.126\.55\.95/' || exit 0
echo 'Retrying Volition after the private Tailscale address became available.'
docker start volition >/dev/null
attempt=0
while [ "$attempt" -lt 30 ]; do
    health=$(docker inspect --format '{{.State.Health.Status}}' volition)
    if [ "$health" = healthy ]; then
        docker exec volition python -m volition.smoke
        exit 0
    fi
    attempt=$((attempt + 1))
    sleep 2
done
echo 'Volition started but did not become healthy within 60 seconds.' >&2
exit 1
