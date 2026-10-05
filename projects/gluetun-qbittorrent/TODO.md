# TODO

Goal: **qBittorrent → Gluetun → WireGuard → NordVPN → Internet** on a Synology DS225+ (DSM 7.4.1, Container Manager 24.0.2), run as a Container Manager Project (Docker Compose).

Hard requirements:

- qBittorrent has no internet access if Gluetun or the VPN fails (kill switch).
- DSM management interface is not exposed through the VPN.
- Existing services keep their current published-port setup; Sonarr follows the same pattern.
- Downloads live in a normal Synology shared folder, outside the container.
- Configuration survives container restarts and upgrades.
- Public IP is verified as the VPN provider's IP before qBittorrent downloads anything.

Working method: one stage at a time, one action at a time, confirm before moving on.

## Stages

- [x] 1. Check prerequisites on the Synology (done 2026-09-20)
  - DS225+, DSM 7.4.1, Container Manager 24.0.2, Docker Compose v2.20.1, 17.7 GB RAM, 5.7 TB free on `/volume1`.
  - `/dev/net/tun` present; `tun`, `iptable_nat`, `iptable_mangle`, `nf_conntrack` loaded.
  - LAN `192.168.178.0/24`, NAS `192.168.178.110`. Docker subnets in use: `172.17`–`172.20`.
  - Watchtower only touches containers named in its command list, so new `gluetun`/`qbittorrent` containers are safe.
  - Shared folders `docker` and `download` exist; existing files in `download` are owned by `master:users` (uid 1026, gid 100).
  - Decided: VPN provider is **NordVPN** (existing subscription, WireGuard/NordLynx via Gluetun). Proton VPN and AirVPN are the fallbacks if inbound port forwarding turns out to matter.
  - Decided: qBittorrent runs as the dedicated `downloader` account (uid 1031, gid 100, `nologin`), not `master`.
- [x] 2. Create the required folders (done 2026-09-20)
  - `/volume1/docker/gluetun`, `/volume1/docker/qbittorrent/config`, `/volume1/download/qbittorrent`; mode 775, owner `master:users`.
- [x] 3. Obtain the NordVPN WireGuard private key (done 2026-09-20)
  - Key comes from the NordVPN API using an access token (dashboard → access tokens), not from the UI.
  - Stored only in `/volume1/docker/gluetun/.env` on the NAS (mode 600, `master`). Not in this repo.
  - The access token is no longer needed and can be revoked in the NordVPN dashboard.
- [x] 4. Create a Container Manager project with Gluetun only (done 2026-09-20)
  - Project `gluetun-qbittorrent`, path `/volume1/docker/gluetun`, compose file in this repo at `projects/gluetun-qbittorrent/docker-compose.yml`.
  - Created through the Container Manager UI; qBittorrent joins this same project in stage 6.
- [x] 5. Start Gluetun and verify the VPN connection and external IP (done 2026-09-20)
  - Control server (`127.0.0.1:8000` on the NAS) reports `running`; exit IP is in Amsterdam, NL (NordVPN P2P server), different from the NAS's home IP.
- [x] 6. Add qBittorrent to the same project using Gluetun's network namespace (done 2026-09-20)
  - `network_mode: "service:gluetun"`, `depends_on` gluetun `service_healthy` + `restart: true`; runs as `downloader` (1031:100).
  - Applied via Container Manager: stop project → Action → Build (Build is greyed out while running).
  - Verified: Gluetun healthy before qBittorrent started; VPN exit still NL (different from home IP); `/volume1/download/qbittorrent` and config now owned by `downloader`.
  - Web UI port 8080 is published on Gluetun and answers HTTP 200 from the LAN (stage 7 still needs login and hardening).
- [x] 7. Make the qBittorrent Web UI accessible from the LAN (done 2026-09-20)
  - `http://192.168.178.110:8080`, user `admin`. Port 8080 is published by Gluetun on all NAS interfaces (LAN + Tailscale); Gluetun's control port 8000 stays on 127.0.0.1.
  - Temporary first-start password replaced with a generated 24-character password via the Web API (login returns 204, not "Ok.", on qBittorrent 5.x). The password is not stored in this repo; save it in a password manager.
  - Lost password recovery: stop the project, remove the `WebUI\Password_PBKDF2` line from `/volume1/docker/qbittorrent/config/qBittorrent/qBittorrent.conf`, start again and read the new temporary password from the container log.
  - Container Manager cannot start `qbittorrent` on its own ("must join at least one network"); start/stop it from the project (Project → Start), not from the Container list.
  - Considered but not done: passwordless access from the Tailscale subnet (needs the source address qBittorrent sees from Tailscale first).
- [x] 8. Map the Synology downloads folder and check permissions (done 2026-09-20, real download test moves to stage 9)
  - qBittorrent `DefaultSavePath=/downloads/`, `TempPath=/downloads/incomplete/` → `/volume1/download/qbittorrent` (owner `downloader:users`, 775, same volume as the temp path). 5.7 TB free.
  - Container already writes its config as `downloader`; the first real write to `/downloads` is confirmed in stage 9 with a test torrent.
  - Open: files created by the container may be 644 (not group-writable) unless `UMASK=002` is set; check the mode of the first downloaded file and add `UMASK=002` to the qbittorrent service if `master`/SMB users need to delete or move downloads.
- [x] 9. Test the kill switch by deliberately stopping or breaking the VPN (done 2026-09-20)
  - Reusable test: `projects/gluetun-qbittorrent/scripts/kill-switch-test.sh` (copy to the NAS, run with `sudo sh`; it restores Gluetun and qBittorrent on exit).
  - Baseline: qBittorrent's own outbound IP equals Gluetun's exit IP (NL), not the home IP.
  - Tunnel interface `tun0` down: qBittorrent times out on both a DNS name and a raw IP, so nothing leaks.
  - Gluetun container stopped: qBittorrent keeps running but only has `lo`; DNS and raw-IP requests fail; the LAN Web UI is unreachable.
  - Known behaviour: after Gluetun is stopped and started again outside Compose, qBittorrent must be restarted to re-join its network (it stays offline until then, which is the safe direction). `depends_on ... restart: true` only applies to Compose/project operations.
  - Open: process umask is 0022, so downloaded files are 644/755 (not group-writable). Add `UMASK=002` to the qbittorrent service if `master`/SMB users need to modify downloads.
- [x] 10. Port forwarding: decided outbound-only on NordVPN (2026-09-20)
  - NordVPN offers no port forwarding, so peers cannot connect in; downloads work, rare torrents and seeding are slower. Revisit by switching provider (Proton = automatic via Gluetun, AirVPN = manual fixed port + `FIREWALL_VPN_INPUT_PORTS`) if that becomes a problem.
  - Listening port stays fixed at 6881 with UPnP/NAT-PMP turned off; applied in stage 11.
- [x] 11. Set sensible qBittorrent defaults (done 2026-09-20)
  - Written to `qBittorrent.conf` while the project was stopped (the file is world-writable; the app overwrites it on shutdown, so never edit it while running). qBittorrent kept every key after a restart, so all are recognised.
  - UPnP/NAT-PMP off, fixed port 6881, LSD off, DHT/PEX on, encryption "prefer", 3 active downloads / 5 active torrents, stop seeding at ratio 2.0, "Run external program" off, save path `/downloads`.
  - `UMASK=002` added to the qbittorrent service: new files are 664 / dirs 775, so the `users` group (master, SMB) can edit them.
  - Not done on purpose: binding qBittorrent to `tun0` (the Gluetun firewall already fails closed; binding adds fragility if the tunnel briefly disappears).
  - Updating the images: Watchtower ignores these two containers by design. Update with Project → Action → Build (stop the project first), then re-run `projects/gluetun-qbittorrent/scripts/kill-switch-test.sh`.
- [ ] 12. Prowlarr (planned 2026-09-21, parked by the user: "not now"; pick up when asked)
  - [x] 12a. Placement decided (2026-09-21): Prowlarr is NOT behind Gluetun (indexers often block VPN IPs). Indexers and Sonarr/Radarr are chosen later inside Prowlarr.
  - [x] 12b. Prowlarr deployed (2026-09-21): `/volume1/docker/prowlarr/config` (`downloader:users`), `prowlarr` service in `docker-compose.yml` (`lscr.io/linuxserver/prowlarr`, port 9696, PUID 1031 / PGID 100 / UMASK 002), applied via project stop → Build. UI answers HTTP 200 on `100.126.55.95:9696`; VPN and qBittorrent unaffected.
  - [x] 12c-1. Authentication set (2026-09-21): Forms login, user `admin`, generated 24-character password via the Prowlarr API (`PUT /api/v1/config/host/{id}` answers 202, not 200). Verified: good password logs in, wrong one is refused, the UI redirects to the login page, API calls need the API key. The password is not stored in this repo; save it in a password manager. The API key lives only in `/volume1/docker/prowlarr/config/config.xml`.
  - [x] 12c-2. qBittorrent added as download client in Prowlarr (2026-09-21): `gluetun:8080`, user `admin`, category `prowlarr`. Prowlarr's connection test passed (the container reaches qBittorrent over the shared Docker network) and the client is saved and enabled.
  - [x] 12d. Indexers and end-to-end test (2026-09-21): added and tested two public, legal-content indexers, LinuxTracker (Linux ISOs) and Internet Archive; Prowlarr health is clean. Search works on both (Internet Archive is slow and sometimes returns an empty response, so query a single indexer with `indexerIds=`). A search-and-grab of `slitaz-rolling-preinit 02112025.iso` (43 MB) went Prowlarr → qBittorrent (through the VPN) and finished in about 10 s: full size on disk, owner `downloader:users`, mode 775 (group-writable, so `UMASK=002` works). Other indexers can be added in the Prowlarr UI (Indexers → Add Indexer); private trackers need the user's own credentials.
  - Left in place: the test ISO in `/volume1/download/qbittorrent` and its torrent (category `prowlarr`); delete it in qBittorrent (remove with files) when no longer wanted.
  - [x] 12e-1. Gateway tile (2026-09-21): Prowlarr tile after qBittorrent, `rel="noopener noreferrer"`; a click lands on Prowlarr's login page (tested in Chrome). Backup `index.html.bak-2026-09-21b`; `NOTES.md` in `/volume1/docker/status-page` updated.
  - [x] 12e-2. `README.md` and `CHANGELOG.md` written (2026-09-21). Nothing is committed yet: the first commit waits for the user's go-ahead.
- [ ] 13. Sonarr (deployed; first-run setup pending; 2026-09-27)
  - [x] 13a. Added the LinuxServer Sonarr service to `docker-compose.yml`: PUID 1031, PGID 100, UMASK 002, Europe/Amsterdam, restart unless-stopped, UI port 8989 using the same published-port pattern as existing apps, and mounts for `/config`, the shared `/downloads` path, and the existing TV library at `/tv`.
  - [x] 13b. Documented initial authentication, `/tv` root folder, and qBittorrent completed-download import setup in `README.md`; Prowlarr integration is optional for searching/grabbing releases.
  - [x] 13c-1. Created `/volume1/docker/sonarr/config`, backed up the previous Compose file, and started only the Sonarr service using `--no-deps` so existing containers were not restarted (2026-09-27).
  - [x] 13c-2. Verified Sonarr responds on port 8989 and, as its service user, can read/write `/downloads` and `/tv` (2026-09-27).
  - [x] 13c-3. Completed first-run authentication and configured `/tv` as the series root (2026-09-27). `/tv` maps to `/volume1/video/TV Shows`, also mounted on the Mac as `/Volumes/video/TV Shows`.
  - [x] 13c-4. Added qBittorrent as Sonarr's download client at `gluetun:8080` with the Sonarr-specific `tv-sonarr` category (2026-09-27).
  - [x] 13c-5. Added a Sonarr tile to the NAS gateway and regenerated its status data; the page shows Sonarr running in the existing container list (2026-09-27).
  - [ ] 13c-6. Verify a real completed-episode import and Plex pickup. Sonarr imports downloads it is tracking; other files in the downloads folder need manual import.

## Next: switch VPN provider to AirVPN (user has an AirVPN account, 2026-09-21)

Why: AirVPN allows a reserved, fixed forwarded port (NordVPN has none), so seeding and inbound peers work.

- [x] A1. AirVPN Config Generator (done 2026-09-21 by the assistant via Chrome, user logged in): Linux, WireGuard, Netherlands, device "Default". The generator downloaded `AirVPN_Netherlands_UDP-1637-Entry3.conf` to `~/Downloads`; the values were moved to the NAS `.env` without being printed and the file was deleted. Regenerate at `https://airvpn.org/generator/` if the key is ever needed again.
- [x] A2. Forwarded port reserved (2026-09-21): **25518**, TCP+UDP, IPv4+IPv6, all devices, local port 25518, at `https://airvpn.org/ports/` (5 ports allowed, 1 used).
- [x] A3. `/volume1/docker/gluetun/.env` (mode 600) now holds `WIREGUARD_PRIVATE_KEY`, `WIREGUARD_PRESHARED_KEY`, `WIREGUARD_ADDRESSES` (IPv4 only, `10.160.90.139/32`) for AirVPN, plus `NORDVPN_WIREGUARD_PRIVATE_KEY` for the fallback.
- [x] A4. Switched (2026-09-21): `docker-compose.yml` uses `VPN_SERVICE_PROVIDER=airvpn`, `SERVER_COUNTRIES=Netherlands`, `FIREWALL_VPN_INPUT_PORTS=25518`; qBittorrent `Session\Port=25518` (edited while the project was stopped). The previous NordVPN setup is kept as `docker-compose.nordvpn.yml` (use its `.env` key `NORDVPN_WIREGUARD_PRIVATE_KEY`; to fall back, copy it over `docker-compose.yml` on the NAS, revert `Session\Port` to 6881, project stop → Build).
- [x] A5a. Verified: VPN status `running`, exit `213.152.186.188` (NL, Global Layer, an AirVPN network) vs home IP `77.250.34.94`; qBittorrent, Prowlarr and the gateway answer. AirVPN's "Test open" shows TCP 25518 IPv4 **Open** (IPv6 times out: containers are IPv4 only, irrelevant).
- [x] A5b. Kill switch re-tested on AirVPN (2026-09-21, `projects/gluetun-qbittorrent/scripts/kill-switch-test.sh`): baseline qBittorrent egress IP = Gluetun's AirVPN exit (NL), not the home IP; `tun0` down → qBittorrent times out on DNS and raw IP (rc=28); Gluetun stopped → qBittorrent only has `lo`, requests fail (rc=6 / 7), LAN Web UI unreachable; restore → back on an AirVPN IP. qBittorrent process umask is now 0002. Gluetun picks a different AirVPN server after each restart; the forwarded port 25518 is per account, so it stays valid. The `recovered by itself` line of the script is misleading: the script brings the interface back up itself.
- [ ] A6. README and first commit; confirm in qBittorrent that seeding is no longer "Stalled" once peers connect; optionally cancel the NordVPN subscription when the fallback is no longer wanted.

## Notes

- NAS is reachable over SSH as `ok040` (user `master`, administrator, no passwordless sudo).
- Never commit WireGuard keys or `.env` files; see `.gitignore`.

## LazyLibrarian (books; deployed 2026-10-01, UI setup open)

Readarr is retired and its image deprecated, so LazyLibrarian is used instead.

- [x] Add the service to `docker-compose.yml` and create `/volume1/docker/lazylibrarian/config` on the NAS.
- [x] Copy the Compose file to the NAS and start the service (done 2026-10-01, `up -d --no-deps lazylibrarian`; runs as uid 1028 because only `calibre` can write to `/volume1/books/Library`).
- [x] First setup in the UI (`:5299`): login set, qBittorrent connected (`gluetun:8080`, category `books`), calibredb at `/usr/bin/calibredb`, library `/books/Library` (done 2026-10-01).
- [x] Search providers: LazyLibrarian is a Prowlarr application with full sync; 6 indexers with book categories synced (2026-10-01).
- [x] Verify one real book is grabbed, imported into the Calibre library and visible in Calibre-Web (done 2026-10-02, *The Ghost Writer*; Kindle delivery verified 2026-10-05).
- [ ] Watch `kindle-check.log` for the first real import, and revisit the 1,000-file threshold once more bad EPUBs are known.
- [ ] Mark the wanted books as `Wanted` in LazyLibrarian (879 of 921 are `Skipped`, so almost nothing is searched).
