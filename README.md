# synology-nas

Configuration, Compose projects, and working notes for services running on a Synology DS225+ (DSM 7.4, Container Manager). One project per subdirectory under `projects/`; each has its own README with the details.

## Projects

| Project | What |
|---|---|
| [host](projects/host/) | DSM-level setup: hardware, users and UIDs, shared folders, scheduled tasks, backups, rebuild order, secret names. **Start here to rebuild.** |
| [gluetun-qbittorrent](projects/gluetun-qbittorrent/) | qBittorrent, Prowlarr, Sonarr and LazyLibrarian; torrent traffic is routed through Gluetun with a hard kill switch. |
| [jellyfin](projects/jellyfin/) | Jellyfin media server, read-only alongside Plex — Music and Audiobooks libraries. |
| [immich](projects/immich/) | Immich photo management (server, machine learning, Postgres, Valkey), version pinned. |
| [calibre-web](projects/calibre-web/) | Calibre-Web front end for the Calibre library, with the kepubify workaround. |
| [keeper](projects/keeper/) | Keeper Markdown notes service, Tailscale-only, digest-pinned. |
| [watchtower](projects/watchtower/) | Image update reporting and selective auto-update, with ntfy notifications. |
| [tailscale-gateway](projects/tailscale-gateway/) | The NAS's Tailscale node (container, no Compose file on the NAS). |
| [tailscale-access](projects/tailscale-access/) | Tailscale access policy notes: how the home NAS and the remote backup target (OK035) are reached, and why DSM on OK035 is blocked by default. |
| [status-page](projects/status-page/) | The Web Station homepage and the script that feeds its status section. |

Everything here was captured from the running NAS on 2026-10-01. Secrets are not stored: each project lists the names it needs, and `.env.example` files show the shape.

This is written for one household NAS, not as a reusable product. The containers and their data live on the NAS; this repo holds the Compose projects and the notes.
