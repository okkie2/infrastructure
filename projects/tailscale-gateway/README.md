# tailscale-gateway

The NAS's Tailscale node, run as a container with a real TUN interface instead of the DSM package. It is the only way OK040 can originate connections to the tailnet (the Hyper Backup run to OK035 needs that) and it is also how you reach OK040 remotely.

| Item | Value |
|---|---|
| Container | `tailscale-tailscale-1` (the name Container Manager gave it; do not rename by CLI) |
| Image | `tailscale/tailscale:stable`, auto-updated by Watchtower |
| Tailscale name / IP | `ok040-gateway`, `100.126.55.95` |
| Mode | `network_mode: host`, `privileged: true`, `TS_USERSPACE=false` |
| State | `/volume1/docker/tailscale-gateway` mounted at `/var/lib/tailscale` |
| Compose file | None on the NAS. [`docker-compose.reconstructed.yml`](docker-compose.reconstructed.yml) is rebuilt from `docker inspect`. |

## Rebuild

1. `mkdir -p /volume1/docker/tailscale-gateway`.
2. Create a reusable, non-expiring auth key in the Tailscale admin console (Settings → Keys).
3. Either run `sudo env TS_AUTHKEY=<key> docker compose -f docker-compose.reconstructed.yml up -d`, or create the container in Container Manager with the same environment and mount.
4. In the admin console, disable key expiry for `ok040-gateway` and check that the IP is `100.126.55.95`. A new node gets a new IP; the access policy ([tailscale-access](../tailscale-access/)), Keeper's port binding and the homepage tiles all use that address, so update them if it changes.

## Why `TS_STATE_DIR` matters

On 2026-09-11 the container lost its identity after a reboot. It had the state folder mounted but no `TS_STATE_DIR`, so `tailscaled` kept state in memory, registered a new node on every restart and eventually got stuck at `NeedsLogin` when the baked-in auth key was rejected. With `TS_STATE_DIR=/var/lib/tailscale` set, `tailscaled.state` is written to the mount and the identity survives restarts. If the node comes up as a new device after a restore, check that file exists first.

## Watchtower

Watchtower is told this container by name (`tailscale-tailscale-1`). If the container is ever renamed, update `command:` in [watchtower](../watchtower/) or it silently stops updating it.

## Other nodes on the tailnet (2026-10-01)

`ok035` (backup target, `100.74.138.41`), `iphone-joost`, `ipad-air-10-5`, `macbook-joost`, and a second-account MacBook (`macbook-air`).
