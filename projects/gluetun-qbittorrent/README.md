# synology-nas

Configuration and notes for running **qBittorrent**, **Prowlarr**, and **Sonarr** on a Synology DS225+ (DSM 7.4, Container Manager). Torrent traffic goes through a VPN and **stops completely if the VPN fails**; Sonarr manages the existing TV library.

```
qBittorrent ──► Gluetun ──► WireGuard ──► AirVPN (Netherlands) ──► Internet
                  ▲
Prowlarr ─────────┘  (talks to qBittorrent's Web UI at gluetun:8080; itself not behind the VPN)
Sonarr (8989) ───────► /tv (existing Plex TV library)
```

It is written for one household NAS, not as a reusable product. The repo holds the Compose project, a kill-switch test and the working notes; the containers and their data live on the NAS.

## What you get

- **Kill switch.** qBittorrent has no network of its own (`network_mode: "service:gluetun"`). With the tunnel down, or Gluetun stopped, it can reach nothing. `projects/gluetun-qbittorrent/scripts/kill-switch-test.sh` proves it.
- **Inbound peers.** AirVPN forwards one fixed port (see [Configuration](#configuration)) to qBittorrent, so seeding works.
- **Web UIs.** qBittorrent on port 8080 and Prowlarr on 9696 follow the existing published-port setup. Sonarr uses the same pattern on port 8989.
- **Sonarr deployed.** Sonarr is running on port 8989, authentication is enabled, `/tv` points to the existing Plex TV folder, and qBittorrent is configured at `gluetun:8080`. A real completed-episode import and Plex pickup have not yet been verified.
- **Persistence.** Settings live in `/volume1/docker/<service>/config`; downloads go to the normal shared folder `/volume1/download/qbittorrent`. Both survive restarts and image updates.
- **Fallback.** `projects/gluetun-qbittorrent/docker-compose.nordvpn.yml` is the previous NordVPN setup (no port forwarding).

## Quick start

Assumes SSH access to the NAS as `ok040` and a running Container Manager. Nothing secret is stored in this repo.

1. **Create the folders** (the `downloader` DSM user, uid 1031 / gid 100, runs the containers):

   ```sh
   ssh ok040 'mkdir -p /volume1/docker/gluetun /volume1/docker/qbittorrent/config /volume1/docker/prowlarr/config /volume1/download/qbittorrent \
     && mkdir -p /volume1/docker/sonarr/config \
     && chmod 775 /volume1/docker/gluetun /volume1/docker/qbittorrent /volume1/docker/qbittorrent/config /volume1/docker/prowlarr /volume1/docker/prowlarr/config /volume1/docker/sonarr /volume1/docker/sonarr/config /volume1/download/qbittorrent'
   ```

2. **Create the private `.env`.** In the AirVPN Client Area, use the Config Generator (WireGuard, Linux, Netherlands) and reserve a forwarded port at `https://airvpn.org/ports/` (TCP+UDP, remote = local port). Copy `.env.example` to `/volume1/docker/gluetun/.env` on the NAS, fill it in and lock it down:

   ```sh
   ssh ok040 'chmod 600 /volume1/docker/gluetun/.env'
   ```

3. **Copy the Compose file** to the NAS (the SFTP subsystem is off, so pipe it through SSH):

   ```sh
   ssh ok040 'cat > /volume1/docker/gluetun/docker-compose.yml' < projects/gluetun-qbittorrent/docker-compose.yml
   ```

4. **Create the project** in DSM: Container Manager → Project → Create. Name `gluetun-qbittorrent`, path `/docker/gluetun`, "Use existing docker-compose.yml", no web portal, start it.

5. **Check the VPN** (control server listens on the NAS only):

   ```sh
   ssh ok040 'curl -s http://127.0.0.1:8000/v1/vpn/status; echo; curl -s http://127.0.0.1:8000/v1/publicip/ip; echo; curl -s https://ipinfo.io/ip'
   ```

   The exit IP must differ from the last line (your home IP).

6. **First logins.** Read qBittorrent's temporary admin password from its container log (Container Manager → Container → `qbittorrent` → Log) and set your own; set a Forms login in Prowlarr. Then in Prowlarr add qBittorrent as a download client (`gluetun`, port 8080). Set qBittorrent's listening port to the forwarded port.

7. **Sonarr setup (partly complete).** Sonarr is deployed on port 8989. Authentication is enabled, and `/tv` is configured as the series root; the Compose mount maps `/tv` to NAS `/volume1/video/TV Shows`, the folder also mounted on a Mac as `/Volumes/video/TV Shows`. Add qBittorrent as Sonarr's download client at host `gluetun`, port `8080`, with the qBittorrent Web UI login. This lets Sonarr track downloads it manages and import completed episodes from `/downloads`. The `/downloads` path maps to the same qBittorrent downloads directory inside both containers. Prowlarr integration is optional and only needed if Sonarr will search for releases through Prowlarr. Plex is expected to scan its already-configured TV root; automatic pickup has not been verified.

## Configuration

| What | Where |
| --- | --- |
| Stack definition | `docker-compose.yml` (project `gluetun-qbittorrent`) |
| Secrets (WireGuard keys, address) | `/volume1/docker/gluetun/.env` on the NAS, mode 600; template in `.env.example` |
| Forwarded port | `FIREWALL_VPN_INPUT_PORTS` in the Compose file, and qBittorrent's listening port (`Session\Port`); both must equal the port reserved at AirVPN |
| Web UIs | qBittorrent `http://<nas>:8080`, Prowlarr `http://<nas>:9696`, Sonarr `http://<nas>:8989` (same published-port pattern as existing apps) |
| Service config | `/volume1/docker/qbittorrent/config`, `/volume1/docker/prowlarr/config`, `/volume1/docker/sonarr/config` |
| Downloads | `/volume1/download/qbittorrent` (files are group-writable: `UMASK=002`) |
| LazyLibrarian (deployed; runs as uid 1028 `calibre` for write access to the library) | `http://<nas>:5299`; config `/volume1/docker/lazylibrarian/config`; Calibre library `/books/Library` (NAS `/volume1/books/Library`); set Processing → Calibredb import program to `/usr/bin/calibredb` |
| Sonarr paths | `/downloads` for qBittorrent downloads; `/tv` for the existing `/volume1/video/TV Shows` library |

## Operating it

- **Change the Compose file or update images:** stop the project, then Action → Build (Build is greyed out while it runs). Watchtower deliberately ignores these containers.
- **Restart qBittorrent** from the project (Project → Restart), never from the Container list: Container Manager refuses to start it alone ("must join at least one network"). If Gluetun is restarted outside Compose, restart qBittorrent too, or it stays offline (the safe direction).
- **Edit `qBittorrent.conf`** only while the project is stopped: the app rewrites it on shutdown. The file is world-writable, the folder is not, so edit it in place.
- **Test the kill switch** after any VPN change (needs `sudo` on the NAS; it restores everything itself):

  ```sh
  ssh ok040 'cat > /tmp/kill-switch-test.sh' < projects/gluetun-qbittorrent/scripts/kill-switch-test.sh
  ssh -t ok040 'sudo sh /tmp/kill-switch-test.sh; rm -f /tmp/kill-switch-test.sh'
  ```

- **Fall back to NordVPN:** from the repository root, run `ssh ok040 'cat > /volume1/docker/gluetun/docker-compose.yml' < projects/gluetun-qbittorrent/docker-compose.nordvpn.yml`, set qBittorrent's listening port back to 6881 and rebuild. NordVPN offers no forwarded port, so seeding stalls.

## Limits and known trade-offs

- **qBittorrent's CSRF protection is switched off** (Options → Web UI). With it on, qBittorrent answers "Unauthorized" to any link that arrives from another page, such as the gateway page. Login is still required; the exposure is a malicious page acting through your logged-in browser session. The tiles use `rel="noreferrer"`.
- **Docker on the NAS is IPv4 only**, so only the IPv4 address is used in `WIREGUARD_ADDRESSES`.
- **Gluetun picks a different AirVPN server after every restart.** The forwarded port belongs to the account and stays valid.
- **Prowlarr is not behind the VPN** on purpose (many indexers block VPN addresses). Only two legal public indexers are configured (LinuxTracker, Internet Archive); add others in Prowlarr yourself.
- The homepage at `http://<nas>/` and its status page are separate from this repo; see `/volume1/docker/status-page/NOTES.md` on the NAS.

## More

- [`TODO.md`](TODO.md): the staged plan, what was verified at each step, and what is still open.
- [`CHANGELOG.md`](CHANGELOG.md): what changed and when.
