# Changelog

## 2026-10-01

- Deployed LazyLibrarian (port 5299) as the book manager, because Readarr is retired and its image is deprecated. It publishes port 5299, mounts `/volume1/books` and the qBittorrent downloads, and loads the `universal-calibre` mod so `calibredb` can import into the existing Calibre library (`/books/Library`). It runs as uid 1028 (`calibre`), the only account with write access to the Calibre library ACL, instead of `downloader`. Created `/volume1/docker/lazylibrarian/config` on the NAS; the previous NAS compose file is kept as `docker-compose.yml.bak-20261001`. Login, download clients and the Calibre settings are still to do in the UI.

## 2026-09-27

- Deployed Sonarr on port 8989; first-run authentication is set, `/tv` points at the Plex TV library, and qBittorrent is configured as its download client at `gluetun:8080`.
- Added Sonarr to the NAS gateway as a UI tile; its container appears automatically in the existing live status list.
- Updated project documentation so repository-root Compose and script paths are copy-pasteable.

## 2026-09-21

- Switched the VPN from NordVPN to AirVPN (Netherlands, WireGuard) with a forwarded port opened in Gluetun and set as qBittorrent's listening port; verified with AirVPN's "Test open". The NordVPN setup is kept as `docker-compose.nordvpn.yml`.
- Kill switch re-tested on AirVPN.
- Added Prowlarr to the same project (not behind the VPN), with a Forms login, qBittorrent as its download client, and two public indexers (LinuxTracker, Internet Archive); end-to-end search and grab verified.
- Added qBittorrent and Prowlarr tiles to the NAS gateway page (`rel="noopener noreferrer"`).
- qBittorrent: `UMASK=002`, sensible queue and seeding defaults, CSRF protection turned off (documented in the README).
- Added `README.md`.

## 2026-09-20

- Created the Gluetun + qBittorrent Compose project on NordVPN (WireGuard) as a Container Manager project.
- Verified the VPN exit IP, the LAN Web UI, and the kill switch (`scripts/kill-switch-test.sh`).
