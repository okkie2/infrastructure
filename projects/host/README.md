# host (DSM on OK040)

Everything that is not a container but that the containers depend on. Captured read-only from the NAS on 2026-10-01. Start here when rebuilding: restore the host first, then each project in the order given under [Rebuild order](#rebuild-order).

## Hardware and OS

| Item | Value |
|---|---|
| Model | Synology DS225+ (`synology_geminilakenk_ds225+`), hostname `OK040-DS255Plus` |
| DSM | 7.4.1-90080, kernel 5.10.55+ |
| Storage | One volume, `/volume1` (btrfs), 7.0 TB (1.6 TB used on 2026-10-05), on a **single drive**: WD Red 8 TB (`WD80EFPX`, CMR). The data array `md2` is a RAID1 with one member, **by choice (cost)**, so there is **no disk redundancy**: a dead disk loses the volume. DSM's system partitions show `[U_]` for the empty second bay. Spinning disk, so Immich runs with `DB_STORAGE_TYPE=HDD`. |
| Disk health (2026-10-05) | SMART PASSED; 1,784 power-on hours, 48 power cycles, 30 °C; zero reallocated, pending, offline-uncorrectable and CRC errors; error log empty. No SMART self-test had ever been run before 2026-10-05; two short tests since then completed without error, and weekly quick and monthly extended tests are now scheduled (see Scheduled tasks). |
| GPU | Intel QuickSync, `/dev/dri`. Jellyfin uses it; Immich transcoding is CPU only. |
| SSH | Enabled on **port 9022** (`ssh ok040`), **key-only** since 2026-10-05 (see Access and accounts); the admin account is `master`. `sudo` works without a password. SFTP is off, so copy files with `ssh ok040 'cat > file' < file`. |
| Tailscale | Not the DSM package. The `tailscale-tailscale-1` container is the NAS's Tailscale node. See [tailscale-gateway](../tailscale-gateway/). |

## Packages installed (Package Center)

Container Manager (Docker), Hyper Backup, Web Station, Plex Media Server, SMB Service, File Station, Git, Node.js v20 and v22, Python2, Security Advisor, Storage Manager, Hybrid Share, USB Copy, QuickConnect, Secure SignIn, AntiVirus, plus Synology system packages. Python 3 comes with DSM and is what `status-page` uses (3.8).

## Users

| User | UID | Used for |
|---|---|---|
| `master` | 1026 | Admin account used over SSH; owns the Compose files in `/volume1/docker`. Jellyfin runs as `1026:100`. |
| `calibre` | 1028 | Owns `/volume1/books`; Calibre-Web and LazyLibrarian run as this uid. |
| `downloader` | 1031 | Runs qBittorrent, Prowlarr, Sonarr, Radarr and Bazarr (PUID 1031). Needs rwx on `/volume1/download/qbittorrent`, `/volume1/video/TV Shows` and `/volume1/video/Movies`. |
| `joost` | 1029 | Personal account (home, Notes). Keeper runs as `1029:100`. |
| `katharina`, `music-listener`, `guest`, `admin` | 1030, 1027, 1025, 1024 | Household and service accounts. `admin` is the built-in account and is **disabled** (expired; confirmed 2026-10-05, and Security Advisor's `disable_admin` check passes); `guest` is disabled too. |

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
| DSM Auto Update | root | Wednesdays 05:40 | `synoupgrade --autoupdate` (Synology default). |
| Run security advisor | root | Sundays 03:13 | Security scan (Synology default). |
| Task 7 / Task 8 | root | 1st of the month 00:00 / daily 00:00 | `securityadvisorreport monthly 1` / `securityadvisorreport daily 1` (Synology defaults). |
| SMART Quicktest | root | Saturdays 01:00 | `/usr/bin/smartctl -d sat -t short /dev/sata1` (about 2 minutes). Added 2026-10-05. |
| SMART Extended test | root | first Saturday of the month, 02:00 | `/usr/bin/smartctl -d sat -t long /dev/sata1` (about 13 hours; the drive estimates 784 minutes). Added 2026-10-05; the first run was started by hand at 15:51 that day. Read results with `sudo smartctl -d sat -l selftest /dev/sata1`. |
| SSH rescue | root | triggered (boot-up), **disabled**; run by hand only | `sed -i 's/^PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config && /usr/syno/bin/synosystemctl restart sshd`. Undoes the key-only SSH setting. |
| Boot-up task for `gluetun/start-stack.sh` | root | at boot | Described in [gluetun-qbittorrent](../gluetun-qbittorrent/). **Exists and works (checked 2026-10-05)**: it is a triggered task named "Start Gluetun stack" (Boot-up, enabled, runs `sh /volume1/docker/gluetun/start-stack.sh`) and last ran at 2026-09-27 09:44, one minute after the NAS booted. Triggered tasks are stored in `/usr/syno/etc/esynoscheduler/esynoscheduler.db`, not in the cron-style task list, so `synoschedtask --get` does not show them. |

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

**Hyper Backup to OK035** (remote Synology reached over Tailscale at `100.74.138.41`, port `6281`; settings read from the NAS on 2026-10-05). Two tasks, each with its own share on OK035, both writing to `OK040-DS255Plus_1.hbk`:

| Task | Source folders | Share on OK035 | Backup / integrity check | Versions kept |
|---|---|---|---|---|
| Media Docker | `/audio`, `/books`, `/docker`, `/photo`, `/PlexMediaServer`, `/video` | `Backup C` | Sundays 12:15 / 21:00 | up to 20 (custom retention rule `[[0,2419200,1],[31536000,604800,1]]`, Hyper Backup's own encoding) |
| Timemachine Homes | `/backup`, `/homes`, `/timemachine` | `Backup D` | Sundays 00:15 / 09:00 | up to 25 (same rule) |

- **Results on 2026-10-04:** Media Docker finished at 17:28 (about 5 hours, 128,658 files scanned, about 766 GB at the target); Timemachine Homes at 00:58 (about 43 minutes, about 849 GB). Both integrity checks found no error. The warnings in the log are harmless: special files (qBittorrent's `ipc-socket`, a socket under `/volume1/homes/master`) and Time Machine bands that changed during the backup.
- **Settings both share:** compression on, version rotation on, files deleted at the source are also deleted at the target. **Data encryption is off, transfer encryption is off and certificate verification is off**; the traffic travels inside Tailscale, but the data on OK035 is stored unencrypted.
- **Failure notices probably go nowhere.** Notifications are enabled in the tasks, but DSM's own notification channel is not configured (empty SMTP settings, and Security Advisor's `enable_notification_v3` fails).
- **The status page's "OK035 backup" is a recency proxy**, not a confirmed remote result (see [status-page](../status-page/)). The repositories show there as `Media Docker (Backup C)` and `Backup D`.
- **`/volume1/docker` is backed up** (inside Media Docker), including Immich's library and database dumps; see [immich](../immich/) for what that does and does not protect.
- **Restore has never been tested** and no procedure is recorded. OK035 must be online for any restore.
- **OK035 is only powered up on Sundays**, which is why every backup and integrity check runs on Sundays and why it shows offline the rest of the week. Because OK040 has a single drive, this weekly copy is the **only copy that survives a disk failure**, so up to 7 days of changes can be lost.
- **OK035** is an ordinary Synology on the tailnet. A plan to move it to another site is in `/volume1/docker/BACKUP-INFRA-TODO.md` on the NAS (an older note, partly stale). The access policy is in [tailscale-access](../tailscale-access/).
- **Time Machine**: the `timemachine` share holds `joost.sparsebundle`; the Mac backs up to it over SMB. Hyper Backup then copies that share to OK035 (Timemachine Homes).

## Web Station homepage

`/volume1/web/index.html` is a static page served by Web Station on port 80, with a live status section fed by `status.json`. The source is in [status-page](../status-page/).

## Plex

Plex Media Server runs as a DSM package, not a container, with libraries on `/volume1/video` and `/volume1/audio`. Its configuration lives in the `PlexMediaServer` share and is not captured here.

## Containers that exist on the NAS

16 containers in 6 Compose projects plus one GUI-created container (the Tailscale gateway).

| Project | Containers | Folder in this repo |
|---|---|---|
| `gluetun-qbittorrent` | gluetun, qbittorrent, prowlarr, sonarr, radarr, bazarr, lazylibrarian | [gluetun-qbittorrent](../gluetun-qbittorrent/) |
| `calibre-web` | calibre-web | [calibre-web](../calibre-web/) |
| `immich` | immich_server, immich_machine_learning, immich_postgres, immich_redis | [immich](../immich/) |
| `jellyfin` | jellyfin | [jellyfin](../jellyfin/) |
| `keeper-managed` | keeper | [keeper](../keeper/) |
| `watchtower` | watchtower | [watchtower](../watchtower/) |
| none (GUI-created) | tailscale-tailscale-1 | [tailscale-gateway](../tailscale-gateway/) |

Also on disk, not containers: `/volume1/docker/_scratch/genre-tagging` (one-off Python scripts used for the Jellyfin genre clean-up, see the Jellyfin README) and `/volume1/docker/BACKUP-INFRA-TODO.md` (an older working note, partly stale: it says the gateway IP changed to `100.122.65.70`, but the gateway is `100.126.55.95` again).

A 79 MB crash dump `/volume1/@jellyfin.…core.gz` dates from 2026-09-27 (Jellyfin crashed then); it is safe to delete once nobody needs it.

Images that remain on the NAS without a container: `ghcr.io/okkie2/brain-mcp` (7 old digests; its container is gone and its deploy script `~/brain-mcp-deploy/deploy.sh` was not found).

## Access and accounts

Checked on the NAS on 2026-10-05; no passwords or keys are recorded here.

- **SSH** listens on **port 9022** on every interface (LAN and Tailscale). Since **2026-10-05 it is key-only** (`PasswordAuthentication no` in `/etc/ssh/sshd_config`, original saved as `sshd_config.bak-20261005`), and `master` has **one** key in `~/.ssh/authorized_keys` (the key has no passphrase, so logins prompt for nothing). Verified after the change: a new key login works with `sudo`, and a password login is refused (`Permission denied (publickey)`). DSM can overwrite `sshd_config` on updates or when SSH settings are changed in Control Panel → Terminal & SNMP, so after either run `grep ^PasswordAuthentication /etc/ssh/sshd_config`.
- **Break-glass if the key is lost:** log into DSM in the browser as `master` and run the Task Scheduler task **SSH rescue** (a disabled triggered task, owner root, which sets `PasswordAuthentication yes` again and restarts `sshd`). It was test-run on 2026-10-05 (exit code 0). Never enable it: as a boot-up trigger it would switch password login back on at every boot. Another route is a one-off root script that appends a new public key to `authorized_keys`. Only members of the `administrators` group can use SSH on DSM; that group holds `master` and the disabled `admin`.
- **Admin access:** `master` (uid 1026) is the working admin account and has `sudo` without a password. `joost` is the personal account and is not an administrator. The service accounts (`calibre`, `downloader`) exist to own files and run containers; see the Users table above.
- **Port forwarding:** DSM's own UPnP/port-forwarding list is empty and QuickConnect is off. The router's configuration is not visible from the NAS and is not recorded.
- **Where credentials live:** each application's own login (qBittorrent, Prowlarr, Sonarr, Bazarr, LazyLibrarian, Calibre-Web, Jellyfin, Immich); see Secrets below for the files. Radarr has a Forms login (username `admin`, password in the password manager).

## Network and services

Checked on the NAS on 2026-10-05.

| Item | Value |
|---|---|
| LAN | `eth0` `192.168.178.110/24` (LAN subnet `192.168.178.0/24`); DNS server `213.46.228.196`. `eth1` has only a link-local address. |
| Tailscale | `100.126.55.95` (the gateway container), see [tailscale-gateway](../tailscale-gateway/) |
| Firewall | DSM firewall **on** (profile `default`). Its `INPUT_FIREWALL` chain has four rules: accept loopback, accept established connections, pass the LAN range `192.168.178.0-254`, pass UDP 41641 (Tailscale); no explicit deny rule was visible, so it does not appear to block anything by itself. Read from `iptables` on 2026-10-05; confirm the intent in Control Panel → Security → Firewall. Router port forwarding is not recorded anywhere. |
| QuickConnect / DDNS | QuickConnect is **off** (an ID exists, `enabled` is false); no DDNS records are configured (DSM API, 2026-10-05). |

What listens (bind address in brackets; "all" means LAN and Tailscale):

| Port | Process | Bind | Notes |
|---|---|---|---|
| 80, 443 | nginx | all | Web Station: the gateway homepage |
| 5000, 5001 | nginx | all | DSM over HTTP / HTTPS; Security Advisor flags HTTPS not enforced and the default ports |
| 8084 | nginx | all | Purpose not identified |
| 5357 | nginx | all | WS-Discovery (Windows network discovery) |
| 139, 445 | smbd | all | SMB: shares and Time Machine |
| 9022 | sshd | all | SSH |
| 161 | snmpd | 127.0.0.1 | SNMP is local only |
| 512 | termd | 127.0.0.1 | DSM terminal service |
| 3261, 3263, 3264, 3265 | `scsi_plugin_server` and related | all | From the **ScsiTarget** package (iSCSI); it has no targets or LUNs, but its ports listen on every interface. It is DSM's built-in **SAN Manager**, a system package that DSM does not let you stop or uninstall. |
| 5432 | postgres | 127.0.0.1 | DSM's own database, not Immich's |
| 2283, 5299, 6767, 7878, 8080, 8083, 8096, 8989, 9696 | docker-proxy | all | Immich, LazyLibrarian, Bazarr, Radarr, qBittorrent (published by Gluetun), Calibre-Web, Jellyfin, Sonarr, Prowlarr |
| 8766 | docker-proxy | `100.126.55.95` | Keeper, Tailscale only |
| 8000 | docker-proxy | 127.0.0.1 | Gluetun control server |
| 32400 | Plex Media Server | all | Plex; 32401, 32600 and the "Plex Script Host" ports are local |
| 45139, 61465 | tailscaled | `100.126.55.95` / IPv6 | Tailscale itself |

**Firewall recommendation (not applied).** The DSM firewall is on but has no deny rule, so what keeps the internet out today is the router (no forwards, QuickConnect off). A deny rule adds insurance if a port forward or another network segment ever appears. Caution: the DSM firewall also filters **forwarded** traffic (its `FORWARD_FIREWALL` chain has the same rules), so a deny-all without a Docker allow rule would cut the containers off. Rule order in Control Panel → Security → Firewall (profile `default`, all interfaces):

1. Allow source `192.168.178.0/24` (LAN), all ports (exists).
2. Allow source `100.64.0.0/10` (Tailscale), all ports.
3. Allow source `172.16.0.0/12` (the Docker bridge networks, currently `172.17`–`172.23`), all ports.
4. Allow UDP `41641` from all sources (Tailscale's direct path; exists).
5. **Deny** all other sources, all ports, **last**.

Test before relying on it, with a second SSH session and the DSM tab open: the gateway page over LAN and over Tailscale, a LazyLibrarian search, a qBittorrent download, and a container reaching the internet. To roll back, disable the firewall or delete the deny rule in the same screen. The Sunday Hyper Backup to OK035 is outbound, so replies are covered by the "established" rule, but confirm it after the first Sunday.

Installed DSM packages not described elsewhere in this repo: **ScsiTarget** (iSCSI), **Hybrid Share**, **USB Copy**, **Migration Assistant**, **QuickConnect** (switched off). The Active Backup and Snapshot Replication packages are not installed. **ScsiTarget has no targets and no LUNs**, so it is unused.

## Power schedule

DSM's Task Scheduler lists two power tasks, `PowerOff` and `PowerOn task 0`, both **disabled** (seen in the UI on 2026-10-05). The NAS therefore runs around the clock.

## Automation outside Docker

Things that run on the NAS but are not Compose projects. None of these files are in this repo.

| What | Where | State on 2026-10-05 |
|---|---|---|
| **Keeper recovery watcher** | `~/keeper-deploy/` (`deploy.sh`, `install-recovery.sh`, `keeper-recover-watch.sh`, `recover-tailscale-bind.sh`); installed as `/etc/systemd/system/keeper-recover.service` with `/usr/local/libexec/keeper/` | Keeper binds to the Tailscale address, which only exists once the Tailscale container is up; when Docker starts Keeper too early the start fails. The watcher listens to Docker's event stream and starts Keeper again after Tailscale starts. **Found enabled but never started** since the 2026-09-27 boot (no start timestamp), and started by hand on **2026-10-05 16:02**; it is active, listening to Docker events for the Tailscale container, and systemd lists it under `multi-user.target`, so it starts at boot. After a DSM update, confirm with `systemctl is-active keeper-recover.service`. The old polling timer was retired by the install script; `keeper-recover.timer` in the folder is a leftover. |
| **Ansible (retired)** | `~/ansible.retired-2026-10-05/` (was `~/ansible/`: `site.yml`, role `docker_container`, `group_vars/ok040.yml`, `files/<project>/docker-compose.yml`) | Copies each project's Compose file to `/volume1/docker/<project>/` and runs `docker compose up`. **It looks like it was never run**: Ansible is not installed on the NAS or on the Mac, there is no copy under `~/Code`, there is no `ansible-playbook` in the shell history, and the files date from 2026-09-22. Its copies have drifted from the running files: `gluetun` differs by 43 lines (it lacks Sonarr and LazyLibrarian), `calibre-web` by 5, `watchtower` by 2; Immich matches. It also holds a reconstructed `brain-mcp` file with a stale Tailscale IP. Anyone who installed Ansible and ran the playbook would redeploy old definitions. **Retired on 2026-10-05**: the folder was renamed to `~/ansible.retired-2026-10-05` (reversible, with a `RETIRED.txt` note) and kept for the `brain-mcp` file; it is safe to delete. The repo is the source of truth. |
| `~/find-agent-cli.sh` | home of `master` | Helper that locates an agent CLI (`claude` by default) on DSM. |
| `~/brain-mcp-access-findings.md` | home of `master` | A 2026-09-11 note on remote access for the Brain MCP service (the container no longer exists; see Containers below). |
| `~/repos/ai-rules` | home of `master` | A clone of the `ai-rules` repository. |
| `/volume1/docker/BACKUP-INFRA-TODO.md`, `/volume1/docker/status-page/NOTES.md` | NAS only | Older working notes, partly stale. |

## Docker logging

Container Manager uses Synology's `db` log driver (`"log-driver": "db"` in `/var/packages/ContainerManager/etc/dockerd.json`): each container's log is a SQLite file `log.db` under `/volume1/@docker/containers/<id>/`. Sizes are small (the largest was 7 MB on 2026-10-05). **Watchtower's log stalled**: its last entry is 2026-10-01 11:42, and `docker logs watchtower` hangs (even `--tail 5`) while other containers answer in about a second. See [watchtower](../watchtower/) and [status-page](../status-page/).

## Security Advisor (scan of 2026-10-04)

No failures at danger or risk level; the status page shows 4 warnings, which are the checks that fail: `httpsEnableCheck` (DSM answers on plain HTTP), `usePort5000Check` and `usePort5001Check` (DSM still on its default ports), and `enable_notification_v3` (no notification channel configured). The built-in `admin` check passes.

## Open items (2026-10-05)

- [ ] Find out why Watchtower's log stopped and why `docker logs watchtower` hangs.
- [ ] Immich backup: add a third copy (USB drive and/or encrypted cloud) and test one restore (see [immich](../immich/#backups)). Snapshot Replication is optional.
- [ ] Decide whether the DSM firewall should get a deny rule (recommended rule set under Network and services), and ScsiTarget cannot be removed (system package).
- [ ] Read the result of the first extended SMART test (started 2026-10-05 15:51, due about 05:00 the next morning).
- [ ] Decide whether to add a USB drive (second physical copy) or a second internal disk.
- [ ] Decide on encryption for the OK035 backups, and test a restore once.
- [ ] Configure DSM notifications so a failed backup is seen.

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
