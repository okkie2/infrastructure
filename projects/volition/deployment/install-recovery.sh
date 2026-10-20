#!/bin/sh
# Installs or upgrades the recovery watcher on the Docker host. Run with sudo.
set -eu
workspace=${1:?Pass the directory containing volition-recover-watch.sh, recover-tailscale-bind.sh and volition-recover.service}
for path in /usr/local/libexec/volition /etc/systemd/system/volition-recover.service; do
    test ! -L "$path"
done
# Stop every legacy watcher before installing the renamed one; never leave two recovery writers.
for unit in keeper-recover.service keeper-recover.timer; do
    if systemctl cat "$unit" >/dev/null 2>&1; then
        systemctl stop "$unit"
        systemctl disable "$unit"
    fi
done
# Earlier versions polled with a timer.
if [ -e /etc/systemd/system/volition-recover.timer ]; then
    systemctl stop volition-recover.timer
    systemctl disable volition-recover.timer
    rm -f /etc/systemd/system/volition-recover.timer /etc/systemd/system/timers.target.wants/volition-recover.timer
fi
install -d -o root -g root -m 0755 /usr/local/libexec/volition
install -o root -g root -m 0755 "$workspace/recover-tailscale-bind.sh" /usr/local/libexec/volition/recover-tailscale-bind.sh
install -o root -g root -m 0755 "$workspace/volition-recover-watch.sh" /usr/local/libexec/volition/volition-recover-watch.sh
install -o root -g root -m 0644 "$workspace/volition-recover.service" /etc/systemd/system/volition-recover.service
systemctl daemon-reload
systemctl enable volition-recover.service
systemctl restart volition-recover.service
systemctl is-active volition-recover.service
systemctl is-enabled volition-recover.service
