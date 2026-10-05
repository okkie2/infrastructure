# watchtower

Reports on, and for a few containers applies, image updates. Uses the maintained fork `ghcr.io/nicholas-fedor/watchtower` (upstream `containrrr/watchtower` is archived).

| Item | Value |
|---|---|
| Container | `watchtower`, project `watchtower` in `/volume1/docker/watchtower` |
| Compose file | [`docker-compose.yml`](docker-compose.yml). The ntfy topic is replaced by a placeholder; the real topic is in the NAS copy. |
| Schedule | Every 6 hours (`WATCHTOWER_POLL_INTERVAL=21600`) |
| Notifications | ntfy via Shoutrrr, sent only when something was updated or failed. Pick a hard-to-guess topic and subscribe to it in the ntfy app. The same topic is shared with other senders; see [host → Notifications](../host/README.md#notifications-ntfy). |
| Log level | `debug`, needed so `status-page` can read per-container update status from `docker logs` |

## Which containers it touches

The `command:` list is its scope. On 2026-10-01: `tailscale-tailscale-1`, `calibre-web`, `prowlarr` (updated automatically) and `immich_server`, `immich_machine_learning`, `immich_redis`, `immich_postgres`, `watchtower` (labelled `monitor-only`: reported, never touched).

Not in the list on purpose: `gluetun`, `qbittorrent`, `sonarr`, `radarr`, `bazarr`, `lazylibrarian`, `jellyfin`, `keeper`. Update those by hand (stop, rebuild, then for the VPN stack re-run the kill-switch test). `prowlarr` was added to the list on 2026-09-27.

Immich is monitor-only because its database migrations are one-way, and `IMMICH_VERSION` is pinned in its `.env`.

## Known problem (2026-10-05)

Watchtower's log stopped being written on **2026-10-01 11:42** (last line: "Scheduled next run: 17:42:58"), although the container stays "Up (healthy)". `docker logs watchtower` hangs, even with `--tail 5`, while other containers answer in about a second. The log is only 4 MB in Synology's `db` log driver (see [host → Docker logging](../host/#docker-logging)), so size is not the cause.

**Cause found:** one Watchtower thread was stuck in `pipe_write`, blocked writing a log line because the `db` log driver had stopped reading the container's output pipe. A blocked logger stalls the program, so Watchtower has most likely done **no update checks since about 2026-10-01 17:42**, and its notifications are dead too. The status page shows "unknown" for the same reason. The health check does not notice this.

**Attempted fix, 2026-10-05:** `docker restart watchtower` did not complete. The Watchtower process was gone, but the Docker daemon stayed stuck stopping the container (the `containerd-shim` was still alive, and `docker inspect`/`logs` on this container hung), while all other containers kept working. The ways forward are: wait for the daemon, kill the container's `containerd-shim` process, or restart the Container Manager package (which restarts every container, so plan for downtime). Afterwards consider giving Watchtower the `json-file` log driver with `max-size`/`max-file` in its Compose file so a stalled `db` driver cannot block it again.

Never run `timeout … sudo docker logs watchtower` for diagnosis: the timeout kills `sudo` but leaves the `docker logs` client hanging.

## Gotchas

- `docker exec watchtower /watchtower --run-once` prints to your terminal only; `docker logs` never sees it, so the status page cannot use it.
- This version does not scan on start. It waits the full interval. To force a check, set the interval to `60`, redeploy, wait, then restore `21600` and redeploy.
- The compose file in the repo mounts the Docker socket read-only.
- Apply changes over SSH (Container Manager's Build does not manage this project): `cd /volume1/docker/watchtower && sudo docker compose up -d`.
