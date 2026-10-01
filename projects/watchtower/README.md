# watchtower

Reports on, and for a few containers applies, image updates. Uses the maintained fork `ghcr.io/nicholas-fedor/watchtower` (upstream `containrrr/watchtower` is archived).

| Item | Value |
|---|---|
| Container | `watchtower`, project `watchtower` in `/volume1/docker/watchtower` |
| Compose file | [`docker-compose.yml`](docker-compose.yml). The ntfy topic is replaced by a placeholder; the real topic is in the NAS copy. |
| Schedule | Every 6 hours (`WATCHTOWER_POLL_INTERVAL=21600`) |
| Notifications | ntfy via Shoutrrr, sent only when something was updated or failed. Pick a hard-to-guess topic and subscribe to it in the ntfy app. |
| Log level | `debug`, needed so `status-page` can read per-container update status from `docker logs` |

## Which containers it touches

The `command:` list is its scope. On 2026-10-01: `tailscale-tailscale-1`, `calibre-web`, `prowlarr` (updated automatically) and `immich_server`, `immich_machine_learning`, `immich_redis`, `immich_postgres`, `watchtower` (labelled `monitor-only`: reported, never touched).

Not in the list on purpose: `gluetun`, `qbittorrent`, `sonarr`, `lazylibrarian`, `jellyfin`, `keeper`. Update those by hand (stop, rebuild, then for the VPN stack re-run the kill-switch test). `prowlarr` was added to the list on 2026-09-27.

Immich is monitor-only because its database migrations are one-way, and `IMMICH_VERSION` is pinned in its `.env`.

## Gotchas

- `docker exec watchtower /watchtower --run-once` prints to your terminal only; `docker logs` never sees it, so the status page cannot use it.
- This version does not scan on start. It waits the full interval. To force a check, set the interval to `60`, redeploy, wait, then restore `21600` and redeploy.
- The compose file in the repo mounts the Docker socket read-only.
- Apply changes over SSH (Container Manager's Build does not manage this project): `cd /volume1/docker/watchtower && sudo docker compose up -d`.
