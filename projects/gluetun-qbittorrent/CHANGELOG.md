# Changelog

## 2026-10-05

- Deployed **Radarr** (port 7878) in the `gluetun-qbittorrent` project next to Sonarr: root folder `/movies` (the existing Plex Movies library, nothing imported), renaming off, qBittorrent at `gluetun:8080` with category `radarr`, and registered as a Prowlarr application (3 indexers synced). Added a Radarr tile to the gateway page. No login set yet. The NAS Compose file was backed up as `docker-compose.yml.bak-20261005-radarr` and only the `radarr` service was started.
- Added the LazyLibrarian "Kindle EPUB check": `scripts/kindle-check.py` runs as LazyLibrarian's `EXT_PREPROCESS` hook, counts an EPUB's spine items and sends an ntfy alert above 1,000. It only warns and always exits 0. Enabled through LazyLibrarian's API (no restart); `config.ini` backed up as `config.ini.bak-20261005-preprocess`. Hardened to skip a manifest over 20 MB. Tested locally, in the container as the LazyLibrarian user (one real alert delivered to the phone), and not yet seen on a real import.
- Added `scripts/fix-epub` (Mac helper that rebuilds a fragmented EPUB with Calibre and adds it back to the library). Dry run on book 51 (568 → 66 files) passed; found and fixed a path bug first.
- Documented the book pipeline gotchas and the notification mechanism ([host](../host/README.md#notifications-ntfy)); see the new LazyLibrarian section in the README.
- Reviewed all project docs against the running NAS and corrected them: Hyper Backup sources, shares and settings are now recorded in [host](../host/README.md#backups); the indexer list, Sonarr import status and qBittorrent limits in this README; the boot-up task for `start-stack.sh` (it exists; triggered tasks are not in the cron-style list); Watchtower's stalled log; and an Immich backup plan in [immich](../immich/README.md#backups).

## 2026-10-04

- Calibre-Web email to Kindle works (Infomaniak SMTP, port 465, SSL/TLS). The first attempts failed because the running app held stale mail settings and spoke plain SMTP to the SSL port; fixed by correcting the values and restarting the container. See the [calibre-web README](../calibre-web/README.md#sending-books-to-a-kindle-email).
- *A Fire Upon the Deep* (book 120) never delivered to the Kindle: 1,581 HTML files inside the EPUB. Rebuilt via Calibre (HTMLZ route, 21 files), replaced in the library (original kept in `/volume1/docker/_scratch/epub-backup/`), resent, delivered to the Black Kindle by 2026-10-05.

## 2026-10-02

- qBittorrent queue unblocked: three stalled torrents were holding all 3 download slots. Raised max active downloads to 16, uploads 8, torrents 8 and excluded slow torrents.
- Verified a real book end to end: *The Ghost Writer* (Robert Harris) was grabbed, imported by `calibredb` into `/books/Library` and visible in Calibre-Web.

## 2026-10-01

- Deployed LazyLibrarian (port 5299) as the book manager, because Readarr is retired and its image is deprecated. It publishes port 5299, mounts `/volume1/books` and the qBittorrent downloads, and loads the `universal-calibre` mod so `calibredb` can import into the existing Calibre library (`/books/Library`). It runs as uid 1028 (`calibre`), the only account with write access to the Calibre library ACL, instead of `downloader`. Created `/volume1/docker/lazylibrarian/config` on the NAS; the previous NAS compose file is kept as `docker-compose.yml.bak-20261001`. LazyLibrarian has a login (Basic auth), qBittorrent as download client (`gluetun:8080`, category `books`, connection test passes) and calibredb import into `/books/Library`. Added a healthcheck (`start_period: 600s`, because the Calibre mod reinstalls its packages on every container (re)create). Added a LazyLibrarian tile (`/authors`) to the NAS gateway page. Prowlarr has no combined Torznab feed, so LazyLibrarian was added as a Prowlarr application (API enabled in LazyLibrarian, `fullSync`): Prowlarr pushed the 6 indexers that advertise book categories (BigFANGroup, Knaben, The Pirate Bay and its copy, World-torrent, Zamunda LIFE) as Torznab providers. A forced eBook search sent two torrents to qBittorrent (category `books`); the Calibre import of a finished download is still unverified.

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
