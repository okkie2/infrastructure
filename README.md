# synology-nas

Configuration, Compose projects, and working notes for services running on a Synology DS225+ (DSM 7.4, Container Manager). One project per subdirectory under `projects/`; each has its own README with the details.

## Projects

| Project | What |
|---|---|
| [gluetun-qbittorrent](projects/gluetun-qbittorrent/) | qBittorrent, Prowlarr, and (prepared, not yet deployed) Sonarr, all torrent traffic routed through a VPN via Gluetun with a hard kill switch. |
| [jellyfin](projects/jellyfin/) | Jellyfin media server, read-only alongside Plex — Music and Audiobooks libraries. |

This is written for one household NAS, not as a reusable product. The containers and their data live on the NAS; this repo holds the Compose projects and the notes.
