# synology-nas

Configuration and notes for running **qBittorrent** and **Prowlarr** on a Synology DS225+ (DSM 7.4, Container Manager) so that all torrent traffic goes through a VPN and **stops completely if the VPN fails**.

```
qBittorrent ──► Gluetun ──► WireGuard ──► AirVPN (Netherlands) ──► Internet
                  ▲
Prowlarr ─────────┘  (talks to qBittorrent's Web UI at gluetun:8080; itself not behind the VPN)
```

It is written for one household NAS, not as a reusable product. The repo holds the Compose project, a kill-switch test and the working notes; the containers and their data live on the NAS.

## What you get

- **Kill switch.** qBittorrent has no network of its own (`network_mode: "service:gluetun"`). With the tunnel down, or Gluetun stopped, it can reach nothing. `scripts/kill-switch-test.sh` proves it.
- **Inbound peers.** AirVPN forwards one fixed port (see [Configuration](#configuration)) to qBittorrent, so seeding works.
- **Web UIs on LAN and Tailscale.** qBittorrent on port 8080, Prowlarr on 9696. The DSM interface is not exposed through the VPN.
- **Persistence.** Settings live in `/volume1/docker/<service>/config`; downloads go to the normal shared folder `/volume1/download/qbittorrent`. Both survive restarts and image updates.
- **Fallback.** `gluetun/docker-compose.nordvpn.yml` is the previous NordVPN setup (no port forwarding).

## Quick start

Assumes SSH access to the NAS as `ok040` and a running Container Manager. Nothing secret is stored in this repo.

1. **Create the folders** (the `downloader` DSM user, uid 1031 / gid 100, runs the containers):

   ```sh
   ssh ok040 'mkdir -p /volume1/docker/gluetun /volume1/docker/qbittorrent/config /volume1/docker/prowlarr/config /volume1/download/qbittorrent \
     && chmod 775 /volume1/docker/gluetun /volume1/docker/qbittorrent /volume1/docker/qbittorrent/config /volume1/docker/prowlarr /volume1/docker/prowlarr/config /volume1/download/qbittorrent'
   ```

2. **Create the private `.env`.** In the AirVPN Client Area, use the Config Generator (WireGuard, Linux, Netherlands) and reserve a forwarded port at `https://airvpn.org/ports/` (TCP+UDP, remote = local port). Copy `gluetun/.env.example` to `/volume1/docker/gluetun/.env` on the NAS, fill it in and lock it down:

   ```sh
   ssh ok040 'chmod 600 /volume1/docker/gluetun/.env'
   ```

3. **Copy the Compose file** to the NAS (the SFTP subsystem is off, so pipe it through SSH):

   ```sh
   ssh ok040 'cat > /volume1/docker/gluetun/docker-compose.yml' < gluetun/docker-compose.yml
   ```

4. **Create the project** in DSM: Container Manager → Project → Create. Name `gluetun-qbittorrent`, path `/docker/gluetun`, "Use existing docker-compose.yml", no web portal, start it.

5. **Check the VPN** (control server listens on the NAS only):

   ```sh
   ssh ok040 'curl -s http://127.0.0.1:8000/v1/vpn/status; echo; curl -s http://127.0.0.1:8000/v1/publicip/ip; echo; curl -s https://ipinfo.io/ip'
   ```

   The exit IP must differ from the last line (your home IP).

6. **First logins.** Read qBittorrent's temporary admin password from its container log (Container Manager → Container → `qbittorrent` → Log) and set your own; set a Forms login in Prowlarr. Then in Prowlarr add qBittorrent as a download client (`gluetun`, port 8080). Set qBittorrent's listening port to the forwarded port.

## Configuration

| What | Where |
| --- | --- |
| Stack definition | `gluetun/docker-compose.yml` (project `gluetun-qbittorrent`) |
| Secrets (WireGuard keys, address) | `/volume1/docker/gluetun/.env` on the NAS, mode 600; template in `gluetun/.env.example` |
| Forwarded port | `FIREWALL_VPN_INPUT_PORTS` in the Compose file, and qBittorrent's listening port (`Session\Port`); both must equal the port reserved at AirVPN |
| Web UIs | qBittorrent `http://<nas>:8080`, Prowlarr `http://<nas>:9696`; from outside the house use the NAS's Tailscale address |
| Service config | `/volume1/docker/qbittorrent/config`, `/volume1/docker/prowlarr/config` |
| Downloads | `/volume1/download/qbittorrent` (files are group-writable: `UMASK=002`) |

## Operating it

- **Change the Compose file or update images:** stop the project, then Action → Build (Build is greyed out while it runs). Watchtower deliberately ignores these containers.
- **Restart qBittorrent** from the project (Project → Restart), never from the Container list: Container Manager refuses to start it alone ("must join at least one network"). If Gluetun is restarted outside Compose, restart qBittorrent too, or it stays offline (the safe direction).
- **Edit `qBittorrent.conf`** only while the project is stopped: the app rewrites it on shutdown. The file is world-writable, the folder is not, so edit it in place.
- **Test the kill switch** after any VPN change (needs `sudo` on the NAS; it restores everything itself):

  ```sh
  ssh ok040 'cat > /tmp/kill-switch-test.sh' < scripts/kill-switch-test.sh
  ssh -t ok040 'sudo sh /tmp/kill-switch-test.sh; rm -f /tmp/kill-switch-test.sh'
  ```

- **Fall back to NordVPN:** copy `gluetun/docker-compose.nordvpn.yml` over the Compose file on the NAS, set qBittorrent's listening port back to 6881 and rebuild. NordVPN offers no forwarded port, so seeding stalls.

## Limits and known trade-offs

- **qBittorrent's CSRF protection is switched off** (Options → Web UI). With it on, qBittorrent answers "Unauthorized" to any link that arrives from another page, such as the gateway page. Login is still required; the exposure is a malicious page acting through your logged-in browser session. The tiles use `rel="noreferrer"`.
- **Docker on the NAS is IPv4 only**, so only the IPv4 address is used in `WIREGUARD_ADDRESSES`.
- **Gluetun picks a different AirVPN server after every restart.** The forwarded port belongs to the account and stays valid.
- **Prowlarr is not behind the VPN** on purpose (many indexers block VPN addresses). Only two legal public indexers are configured (LinuxTracker, Internet Archive); add others in Prowlarr yourself.
- The homepage at `http://<nas>/` and its status page are separate from this repo; see `/volume1/docker/status-page/NOTES.md` on the NAS.

## More

- [`TODO.md`](TODO.md): the staged plan, what was verified at each step, and what is still open.
- [`CHANGELOG.md`](CHANGELOG.md): what changed and when.
