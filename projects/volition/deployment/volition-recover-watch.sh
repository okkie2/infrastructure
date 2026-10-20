#!/bin/sh
# Volition listens on the NAS's Tailscale address, which only exists once the Tailscale
# container is up. When Docker starts Volition first, its start fails. This starts it
# again as soon as Tailscale has started. Otherwise it sleeps on Docker's event stream:
# no polling, and nothing is logged unless it acts.
set -u
PATH="$PATH:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"    # systemd's default PATH lacks /usr/local/bin
export PATH
here=$(dirname "$0")
tailscale_container=tailscale-tailscale-1
address=100.126.55.95
interval=${VOLITION_WAIT_INTERVAL:-2}    # seconds; tests shorten it

recover() {
    "$here/recover-tailscale-bind.sh" || echo 'Recovery attempt failed.' >&2
}

# Docker itself may still be starting when the NAS boots.
until docker info >/dev/null 2>&1; do sleep "$interval"; done

# Cover a failure that happened before this watcher was running.
recover

docker events --filter "container=$tailscale_container" --filter event=start --format '{{.Status}}' |
while read -r _; do
    # The container starts a few seconds before its interface has the address.
    attempts=0
    until ip -4 addr show dev tailscale0 2>/dev/null | grep -qF "inet $address/"; do
        attempts=$((attempts + 1))
        [ "$attempts" -ge 30 ] && break
        sleep "$interval"
    done
    recover
done
echo 'Docker event stream ended; exiting so systemd restarts the watcher.' >&2
exit 1
