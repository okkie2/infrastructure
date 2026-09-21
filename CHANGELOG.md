# Changelog

## 2026-09-21

- Switched the VPN from NordVPN to AirVPN (Netherlands, WireGuard) with a forwarded port opened in Gluetun and set as qBittorrent's listening port; verified with AirVPN's "Test open". The NordVPN setup is kept as `gluetun/docker-compose.nordvpn.yml`.
- Kill switch re-tested on AirVPN.
- Added Prowlarr to the same project (not behind the VPN), with a Forms login, qBittorrent as its download client, and two public indexers (LinuxTracker, Internet Archive); end-to-end search and grab verified.
- Added qBittorrent and Prowlarr tiles to the NAS gateway page (`rel="noopener noreferrer"`).
- qBittorrent: `UMASK=002`, sensible queue and seeding defaults, CSRF protection turned off (documented in the README).
- Added `README.md`.

## 2026-09-20

- Created the Gluetun + qBittorrent Compose project on NordVPN (WireGuard) as a Container Manager project.
- Verified the VPN exit IP, the LAN Web UI, and the kill switch (`scripts/kill-switch-test.sh`).
