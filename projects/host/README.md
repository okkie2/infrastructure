# host (DSM on OK040)

Everything that is not a container but that the containers depend on. Captured read-only from the NAS on 2026-10-01. Start here when rebuilding: restore the host first, then each project in the order given under [Rebuild order](#rebuild-order).

## Hardware and OS

| Item | Value |
|---|---|
| Model | Synology DS225+ (`synology_geminilakenk_ds225+`), hostname `OK040-DS255Plus` |
| DSM | 7.4.1-90080, kernel 5.10.55+ |
| Storage | One volume, `/volume1`, 7.0 TB (1.5 TB used on 2026-10-01). Spinning disks, so Immich runs with `DB_STORAGE_TYPE=HDD`. |
| GPU | Intel QuickSync, `/dev/dri`. Jellyfin uses it; Immich transcoding is CPU only. |
| SSH | Enabled; the admin account is `master`. `sudo` works without a password. SFTP is off, so copy files with `ssh ok040 'cat > file' < file`. |
| Tailscale | Not the DSM package. The `tailscale-tailscale-1` container is the NAS's Tailscale node. See [tailscale-gateway](../tailscale-gateway/). |

## Packages installed (Package Center)

Container Manager (Docker), Hyper Backup, Web Station, Plex Media Server, SMB Service, File Station, Git, Node.js v20 and v22, Python2, Security Advisor, Storage Manager, Hybrid Share, USB Copy, QuickConnect, Secure SignIn, AntiVirus, plus Synology system packages. Python 3 comes with DSM and is what `status-page` uses (3.8).

## Users

| User | UID | Used for |
|---|---|---|
| `master` | 1026 | Admin account used over SSH; owns the Compose files in `/volume1/docker`. Jellyfin runs as `1026:100`. |
| `calibre` | 1028 | Owns `/volume1/books`; Calibre-Web and LazyLibrarian run as this uid. |
| `downloader` | 1031 | Runs qBittorrent, Prowlarr and Sonarr (PUID 1031). Needs rwx on `/volume1/download/qbittorrent` and `/volume1/video/TV Shows`. |
| `joost` | 1029 | Personal account (home, Notes). Keeper runs as `1029:100`. |
| `katharina`, `music-listener`, `guest`, `admin` | 1030, 1027, 1025, 1024 | Household and service accounts. `admin` is the built-in account and is still enabled (Security Advisor `disable_admin` finding). |

All share the group `users` (gid 100). UIDs matter because the containers use them for file permissions; recreate the accounts so the numbers match, or change `PUID` in the Compose files.

## Shared folders

`audio` (Music, Audiobooks), `backup`, `books` (Calibre library in `Library`), `docker` (all container state), `download` (qBittorrent downloads), `homes`, `photo` (existing photo archive, read-only to Immich), `PlexMediaServer`, `timemachine`, `video` (Movies, TV Shows), `web` (homepage), `web_packages`.

Permissions are partly Synology ACLs (the `+` in `ls -l`), which a plain `chmod` does not show. After a restore, check them in Control Panel → Shared Folder → Permissions and in File Station → Properties → Permission.

## Scheduled tasks (Control Panel → Task Scheduler)

| Task | Owner | When | What |
|---|---|---|---|
| status-page-refresh | root | daily from 00:30, repeating through the day (last run 18:30) | `python3 /volume1/docker/status-page/gather-status.py` writes `/volume1/web/status.json`. See [status-page](../status-page/). |
| Notes Daily Copy | joost | daily 02:00 | Copies `/volume1/homes/joost/Notes` to `/volume1/homes/joost/Notes-backups/Notes-<timestamp>` and keeps the newest 8. Script below. |
| Media Docker (backup) and verify | root | Sundays 12:15 / 21:00 | Hyper Backup run and verify for the "Media Docker" repo. |
| Timemachine Homes (backup) and verify | root | Sundays 00:15 / 09:00 | Hyper Backup run and verify for the "Timemachine Homes" repo. |
| DSM Auto Update, Run security advisor, Security advisor reports | root | weekly / monthly / daily | Synology defaults. |
| Boot-up task for `gluetun/start-stack.sh` | root | at boot | Described in [gluetun-qbittorrent](../gluetun-qbittorrent/). **Not visible in the task list on 2026-10-01**, though `start-stack.log` shows it ran on 2026-09-27. Check that it still exists. |

Notes Daily Copy script (user-defined script, run as `joost`):

```sh
#!/bin/sh
set -eu
src=/volume1/homes/joost/Notes
backup_root=/volume1/homes/joost/Notes-backups
[ -d "$src" ] || { echo "Source directory not found: $src" >&2; exit 1; }
mkdir -p "$backup_root"
stamp=$(date '+%Y-%m-%d_%H%M%S')
tmp="$backup_root/.Notes-$stamp.partial"
snapshot="$backup_root/Notes-$stamp"
[ ! -e "$tmp" ] && [ ! -e "$snapshot" ] || { echo "Snapshot name already exists: $snapshot" >&2; exit 1; }
cp -a "$src" "$tmp"
mv "$tmp" "$snapshot"
find "$backup_root" -mindepth 1 -maxdepth 1 -type d -name 'Notes-????-??-??_??????' -print | sort -r | awk 'NR > 8' | while IFS= read -r old; do rm -rf -- "$old"; done
```

## Notifications (ntfy)

One mechanism sends alerts to the phone: **ntfy** on the public server `ntfy.sh`, with one private topic that the ntfy app on the phone is subscribed to. The topic is the only secret, because anyone who knows it can read and publish. It is not stored in this repo; the real value is in the NAS copy of the Watchtower Compose file (and a note in `/volume1/docker/BACKUP-INFRA-TODO.md`).

| Sender | How | Message |
|---|---|---|
| [watchtower](../watchtower/) | Shoutrrr URL `ntfy://ntfy.sh/<topic>` in `WATCHTOWER_NOTIFICATION_URL` | "Watchtower: updated …" or "FAILED updating …" |
| [kindle-check.py](../gluetun-qbittorrent/README.md#kindle-epub-check-warn-only-pre-process-hook) (LazyLibrarian hook) | HTTPS POST to the topic, URL read from `kindle-check.conf` | Title "Kindle delivery risk: EPUB badly split" |

To send from any new script, POST to the topic with a distinct title so the senders can be told apart:

```sh
curl -s -m 10 -H "Title: <what raised it>" -H "Tags: warning" -d "<message>" "https://ntfy.sh/<topic>"
```

HTTP 200 with a JSON `message` event means ntfy accepted it. Keep the call short-timed and never let a failed alert fail the job that raised it.

DSM's own notifier is **not** usable for this: `synodsmnotify` only accepts predefined DSM message keys (a free-text title is rejected), and DSM's email notification is not configured on this NAS (empty SMTP settings). Verified 2026-10-05.

## Backups

- **Hyper Backup to OK035** (remote Synology, reached over Tailscale at `100.74.138.41`, port 6281). Two repos, "Media Docker" and "Timemachine Homes", scheduled on Sundays as above. The source folders, retention and encryption settings are **not captured here**: they live in Hyper Backup's own store, which could not be read from SSH. Export or screenshot them from the Hyper Backup UI. The access policy that allows this traffic is in [tailscale-access](../tailscale-access/).
- **Time Machine**: the `timemachine` share holds `joost.sparsebundle`; the Mac backs up to it over SMB.
- **Not covered by anything found**: it is unknown whether `/volume1/docker` (all container config and the Immich database) is in a Hyper Backup source. Check this; without it, a lost volume loses every application's settings.

## Web Station homepage

`/volume1/web/index.html` is a static page served by Web Station on port 80, with a live status section fed by `status.json`. The source is in [status-page](../status-page/).

## Plex

Plex Media Server runs as a DSM package, not a container, with libraries on `/volume1/video` and `/volume1/audio`. Its configuration lives in the `PlexMediaServer` share and is not captured here.

## Containers that exist on the NAS

14 containers in 6 Compose projects plus one GUI-created container (the Tailscale gateway).

| Project | Containers | Folder in this repo |
|---|---|---|
| `gluetun-qbittorrent` | gluetun, qbittorrent, prowlarr, sonarr, lazylibrarian | [gluetun-qbittorrent](../gluetun-qbittorrent/) |
| `calibre-web` | calibre-web | [calibre-web](../calibre-web/) |
| `immich` | immich_server, immich_machine_learning, immich_postgres, immich_redis | [immich](../immich/) |
| `jellyfin` | jellyfin | [jellyfin](../jellyfin/) |
| `keeper-managed` | keeper | [keeper](../keeper/) |
| `watchtower` | watchtower | [watchtower](../watchtower/) |
| none (GUI-created) | tailscale-tailscale-1 | [tailscale-gateway](../tailscale-gateway/) |

Also on disk, not containers: `/volume1/docker/_scratch/genre-tagging` (one-off Python scripts used for the Jellyfin genre clean-up, see the Jellyfin README) and `/volume1/docker/BACKUP-INFRA-TODO.md` (an older working note, partly stale: it says the gateway IP changed to `100.122.65.70`, but the gateway is `100.126.55.95` again).

A 79 MB crash dump `/volume1/@jellyfin.…core.gz` dates from 2026-09-27 (Jellyfin crashed then); it is safe to delete once nobody needs it.

Images that remain on the NAS without a container: `ghcr.io/okkie2/brain-mcp` (7 old digests; its container is gone and its deploy script `~/brain-mcp-deploy/deploy.sh` was not found).

## Rebuild order

1. Install DSM 7.4, create the volume, then the users and shared folders above with the same UIDs.
2. Install Container Manager, Web Station, Hyper Backup, Plex.
3. Restore `/volume1/docker` from backup if it exists. Otherwise recreate each project from this repo and the per-project README.
4. Start [tailscale-gateway](../tailscale-gateway/) first (everything else is reached over it), then the projects in any order: gluetun-qbittorrent, immich, calibre-web, jellyfin, keeper, watchtower.
5. Recreate the Task Scheduler entries, then [status-page](../status-page/).
6. Re-enter secrets from your password manager; none are in this repo.

## Secrets (names only; values are not stored here)

| Where | Names |
|---|---|
| `/volume1/docker/gluetun/.env` | `WIREGUARD_PRIVATE_KEY`, `WIREGUARD_PRESHARED_KEY`, `WIREGUARD_ADDRESSES`, `NORDVPN_WIREGUARD_PRIVATE_KEY` |
| `/volume1/docker/immich/.env` | `DB_PASSWORD` |
| `/volume1/docker/keeper-managed/.env` | `KEEPER_TOKEN` |
| Tailscale gateway container | `TS_AUTHKEY` |
| Watchtower compose | ntfy topic name (treated as private) |
| `/volume1/docker/lazylibrarian/config/kindle-check.conf` | `NTFY_URL` (the same ntfy topic); git-ignored, mode 640 |
| Calibre-Web (Admin → Email Server Settings) | Infomaniak device password "Calibre-Web" for sending to the Kindle |
| Each app's own UI | admin logins for qBittorrent, Prowlarr, Sonarr, LazyLibrarian, Calibre-Web, Jellyfin, Immich |
