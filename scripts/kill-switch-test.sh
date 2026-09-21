#!/bin/sh
D=/usr/local/bin/docker
CP=http://127.0.0.1:8000
fetch() { # $1 = url ; prints rc + output from inside qbittorrent's network namespace
  out=$($D exec qbittorrent curl -s --max-time 8 "$1" 2>&1); rc=$?
  echo "rc=$rc out=$(echo "$out" | head -c 60)"
}
wait_healthy() {
  i=0; while [ $i -lt 45 ]; do
    [ "$($D inspect -f '{{.State.Health.Status}}' gluetun 2>/dev/null)" = healthy ] && return 0
    sleep 2; i=$((i+1)); done; return 1
}
restore() {
  [ "$($D inspect -f '{{.State.Running}}' gluetun 2>/dev/null)" = true ] || $D start gluetun >/dev/null
  wait_healthy && echo "[restore] gluetun healthy" || echo "[restore] gluetun NOT healthy"
}
trap restore EXIT

echo "== 0. context"
echo "home IP (NAS, no VPN): $(curl -s --max-time 8 https://ipinfo.io/ip)"
$D exec qbittorrent sh -c 'command -v curl >/dev/null && echo "curl present in qbittorrent" || echo "NO curl in qbittorrent"'
echo "qbittorrent interfaces: $($D exec qbittorrent sh -c 'ls /sys/class/net' | tr '\n' ' ')"
echo "gluetun interfaces:     $($D exec gluetun sh -c 'ls /sys/class/net' | tr '\n' ' ')"
echo "qbittorrent process umask/uid: $($D exec qbittorrent sh -c 'p=$(pidof qbittorrent-nox | cut -d" " -f1); grep -E "^(Umask|Uid)" /proc/$p/status | tr "\t\n" "  "')"

echo "== 1. baseline (tunnel up)"
echo "gluetun exit IP:        $(curl -s --max-time 5 $CP/v1/publicip/ip | sed -E 's/.*"public_ip":"([^"]+)".*"country":"([^"]+)".*/\1 \2/')"
echo "qbittorrent via DNS:    $(fetch https://ipinfo.io/ip)"
echo "qbittorrent via raw IP: $(fetch http://1.1.1.1/)"

echo "== 2. VPN interface down (gluetun still running)"
IF=$($D exec gluetun sh -c 'ls /sys/class/net' | grep -E '^(wg|tun)[0-9]*$' | head -1)
echo "tunnel interface: ${IF:-NOT FOUND}"
if [ -n "$IF" ]; then
  $D exec gluetun ip link set "$IF" down && echo "interface $IF set down"
  echo "qbittorrent via DNS:    $(fetch https://ipinfo.io/ip)"
  echo "qbittorrent via raw IP: $(fetch http://1.1.1.1/)"
  echo "gluetun status now:     $(curl -s --max-time 5 $CP/v1/vpn/status)"
  $D exec gluetun ip link set "$IF" up 2>/dev/null
  wait_healthy && echo "gluetun recovered by itself" || echo "gluetun did not recover in time"
fi

echo "== 3. gluetun stopped completely"
$D stop gluetun >/dev/null && echo "gluetun stopped"
echo "qbittorrent container state: $($D inspect -f '{{.State.Status}}' qbittorrent)"
echo "qbittorrent interfaces:      $($D exec qbittorrent sh -c 'ls /sys/class/net' | tr '\n' ' ')"
echo "qbittorrent via DNS:         $(fetch https://ipinfo.io/ip)"
echo "qbittorrent via raw IP:      $(fetch http://1.1.1.1/)"
echo "web ui from NAS meanwhile:   $(curl -s -o /dev/null -w 'HTTP %{http_code}' --max-time 5 http://127.0.0.1:8080/ || echo 'unreachable')"

echo "== 4. restore"
$D start gluetun >/dev/null; wait_healthy && echo "gluetun healthy"
$D restart qbittorrent >/dev/null && echo "qbittorrent restarted (re-attached to the new gluetun)"
sleep 12
echo "gluetun exit IP:        $(curl -s --max-time 5 $CP/v1/publicip/ip | sed -E 's/.*"public_ip":"([^"]+)".*"country":"([^"]+)".*/\1 \2/')"
echo "qbittorrent via DNS:    $(fetch https://ipinfo.io/ip)"
echo "web ui from NAS:        $(curl -s -o /dev/null -w 'HTTP %{http_code}' --max-time 5 http://127.0.0.1:8080/)"
