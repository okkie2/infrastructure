# host (DSM on OK040)

Everything that is not a container but that the containers depend on. Captured read-only from the NAS on 2026-10-01. Start here when rebuilding: restore the host first, then each project in the order given under [Rebuild order](#rebuild-order).

## Hardware and OS

| Item | Value |
|---|---|
| Model | Synology DS225+ (`synology_geminilakenk_ds225+`), hostname `OK040-DS255Plus` |
| DSM | 7.4.1-90080, kernel 5.10.55+ |
| Storage | One volume, `/volume1` (btrfs), 7.0 TB (1.6 TB used on 2026-10-05), on a **single drive**: WD Red 8 TB (`WD80EFPX`, CMR). The data array `md2` is a RAID1 with one member, **by choice (cost)**, so there is **no disk redundancy**: a dead disk loses the volume. DSM's system partitions show `[U_]` for the empty second bay. Spinning disk, so Immich runs with `DB_STORAGE_TYPE=HDD`. |
| Disk health (2026-10-18) | SMART PASSED; 2,094 power-on hours, 50 power cycles, 30 °C; zero reallocated, pending, offline-uncorrectable and CRC errors; error log empty. Task Scheduler records quick-test launches, but this drive does not support SMART self-test logging, so actual self-test completion cannot be verified from the drive. Weekly quick and first-Saturday extended tests are scheduled (see Scheduled tasks). |
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
| `joost` | 1029 | Personal account (home, Volition notes). Volition runs as `1029:100`. |
| `katharina`, `music-listener`, `guest`, `admin` | 1030, 1027, 1025, 1024 | Household and service accounts. `admin` is the built-in account and is **disabled** (expired; confirmed 2026-10-05, and Security Advisor's `disable_admin` check passes); `guest` is disabled too. |

All share the group `users` (gid 100). UIDs matter because the containers use them for file permissions; recreate the accounts so the numbers match, or change `PUID` in the Compose files.

## Shared folders

`audio` (Music, Audiobooks), `backup`, `books` (Calibre library in `Library`), `docker` (all container state), `download` (qBittorrent downloads), `homes`, `photo` (existing photo archive, read-only to Immich), `PlexMediaServer`, `timemachine`, `video` (Movies, TV Shows), `web` (homepage), `web_packages`.

Permissions are partly Synology ACLs (the `+` in `ls -l`), which a plain `chmod` does not show. After a restore, check them in Control Panel → Shared Folder → Permissions and in File Station → Properties → Permission.

## Scheduled tasks (Control Panel → Task Scheduler)

| Task | Owner | When | What |
|---|---|---|---|
| status-page-refresh | root | daily from 00:30, repeating through the day (last run 18:30) | `python3 /volume1/docker/status-page/gather-status.py` writes `/volume1/web/status.json`. See [status-page](../status-page/). |
| Volition Daily Copy | joost | daily 02:00 | Runs `/usr/bin/python3 /usr/local/libexec/volition/backup-notes.py`; copies `/volume1/homes/joost/Volition/notes` to `/volume1/homes/joost/Volition-backups/notes-<timestamp>` and keeps the newest 8. |
| Media Docker (backup) and verify | root | Sundays 12:15 / 21:00 | Hyper Backup run and verify for the "Media Docker" repo. |
| Timemachine Homes (backup) and verify | root | Sundays 00:15 / 09:00 | Hyper Backup run and verify for the "Timemachine Homes" repo. |
| DSM Auto Update | root | Wednesdays 05:40 | `synoupgrade --autoupdate` (Synology default). |
| Run security advisor | root | Sundays 03:13 | Security scan (Synology default). |
| Task 7 / Task 8 | root | 1st of the month 00:00 / daily 00:00 | `securityadvisorreport monthly 1` / `securityadvisorreport daily 1` (Synology defaults). |
| SMART Quicktest | root | Saturdays 01:00 | `/usr/bin/smartctl -d sat -t short /dev/sata1` (about 2 minutes). Added 2026-10-05. |
| SMART Extended test | root | first Saturday of the month, 02:00 | `/usr/bin/smartctl -d sat -t long /dev/sata1` (about 13 hours; the drive estimates 784 minutes). Added 2026-10-05; the first run was started by hand at 15:51 that day. `sudo smartctl -d sat -l selftest /dev/sata1` reports that the device does not support self-test logging, so actual completion is unverified. |
| SSH rescue | root | triggered (boot-up), **disabled**; run by hand only | `sed -i 's/^PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config && /usr/syno/bin/synosystemctl restart sshd`. Undoes the key-only SSH setting. |
| Boot-up task for `gluetun/start-stack.sh` | root | at boot | Described in [gluetun-qbittorrent](../gluetun-qbittorrent/). **Exists and works (checked 2026-10-05)**: it is a triggered task named "Start Gluetun stack" (Boot-up, enabled, runs `sh /volume1/docker/gluetun/start-stack.sh`) and last ran at 2026-09-27 09:44, one minute after the NAS booted. Triggered tasks are stored in `/usr/syno/etc/esynoscheduler/esynoscheduler.db`, not in the cron-style task list, so `synoschedtask --get` does not show them. |

## Proposed power and maintenance windows (not applied)

Use **maintenance window** for the recurring time when OK040 is powered on to run backups, integrity checks and disk tests. The term is defined in the repository [glossary](../../GLOSSARY.md). Times below are Europe/Amsterdam local time. This is a proposal; the DSM and Hyper Backup schedules have not been changed.

### Evidence and limits

- The requested weekday availability is **08:00–00:00, Monday–Friday**.
- On 2026-10-04, Timemachine Homes took about **43 minutes** (about 849 GB at the target). Media Docker took about **5 hours 13 minutes** (128,658 files scanned; about 766 GB at the target). These are the only completed run durations available in the repo.
- On 2026-10-18, the Hyper Backup snapshot showed Timemachine Homes successful at 00:18, but did not record its start. Media Docker was still running at 13:42, at least 1 hour 27 minutes after its scheduled time; no completion time was available. Hyper Backup did not retain a usable run archive during inspection.
- The backup integrity tasks were scheduled for 09:00 and 21:00. The available monitor snapshots ended at 11:25 and 21:54, but do not retain start times. Treat **2 hours 25 minutes** as an observed planning allowance, not a proven maximum.
- The weekly SMART Quick Test is scheduled for Saturday 01:00. The first-Saturday Extended Test starts at 02:00 (roughly every four weeks, though calendar months are not exactly four weeks) and the drive estimates **784 minutes (13 hours 4 minutes)**. Task Scheduler logs only the command that starts each test; the drive does not support self-test logging, so actual completion is unverified.
- SMART reported PASSED with no reallocated, pending or uncorrectable sectors. Drive power-on hours rose by about 958 in 40 days in the available disk-prediction snapshots, roughly 24 hours per day. That snapshot period reflects near-continuous operation; it does not establish exactly when the power schedule was enabled.
- The NAS power-schedule screen supports daily, weekend, weekday and individual weekday entries; it does not offer a first-Saturday monthly power-off rule. A simple weekly schedule therefore needs to allow the long test window every Saturday, or use a separately validated date-aware shutdown task.

### Recommended schedule

| Day | Power on | Power off | Purpose |
|---|---:|---:|---|
| Monday–Friday | 08:00 | 00:00 | Match the stated weekday access window. |
| Saturday | 00:45 | 01:30 on other Saturdays; 16:00 on the first Saturday | Add a 00:00 Saturday power-off after Friday use, then wake before the 01:00 Quick Test. The first-Saturday 16:00 shutdown allows the 02:00 Extended Test to finish, with about 56 minutes after the drive's 13:04 estimate. |
| Sunday | 00:00 | 20:15 | Run both backups and integrity checks, with headroom for growth. |

For Sunday, move the Hyper Backup jobs and integrity checks into a tighter sequence:

| Task | Proposed Sunday time | Basis |
|---|---:|---|
| Timemachine Homes backup | 00:15 | Keep its current start. |
| Timemachine Homes integrity check | 03:00 | Allows 2 hours 45 minutes from the backup start, versus the 43-minute completed baseline. |
| Media Docker backup | 06:00 | Leaves 35 minutes after the longest observed integrity-monitor run ending at 05:25 if the check starts at 03:00. |
| Media Docker integrity check | 17:00 | Allows about 10 hours 26 minutes for the backup, twice the only completed 5:13 baseline, plus 34 minutes before the check. |
| Sunday power off | 20:15 | Allows 2 hours 25 minutes for the last observed monitor duration and a further 50-minute margin. |

The Sunday plan assumes the Media Docker backup remains under about **10 hours 26 minutes** and each integrity check finishes within the longest observed **2 hours 25 minutes**. Those are planning limits, not guarantees. Review the first four completed Sunday runs; if a backup approaches its limit, move the start earlier or extend the Sunday power-off time before the next run. Keep OK035 powered on for the whole Sunday window.

The DSM Power Schedule supports weekly day selection but not a first-Saturday exception. For the minimum-uptime plan above, add two date-aware Task Scheduler shutdown actions: at 01:30, power off unless it is the first Saturday; at 16:00, power off only on the first Saturday. Validate these actions on a non-maintenance test day before relying on them. If avoiding custom logic is more important than saving Saturday uptime, use the DSM-only fallback: power off at 16:00 every Saturday, accepting the longer run on the three quick-test-only Saturdays.

### Other scheduled work that must be reconciled

Powering off outside the windows would skip tasks that currently run at 00:00 or 02:00. Before applying the power schedule, move any essential daily work into a powered-on period and check that it completes before shutdown. The Task Scheduler snapshot showed `Volition Daily Copy` at 02:00; the repository also lists a daily Security Advisor report and an Immich database dump, but those two were not visible in that snapshot. Confirm which tasks are enabled and where the Immich dump is scheduled. Hourly status refreshes, Watchtower checks and LazyLibrarian processing will also only run while the NAS is on.

### qBittorrent and disk activity

At the time of inspection there was no qBittorrent process, matching container or qBittorrent configuration in the inspected NAS paths. Its current seeding activity, tracker obligations and live settings could therefore not be verified. The existing project notes record a global seed ratio limit of 2.0, but do not establish that this setting is currently deployed.

Before relying on qBittorrent during the weekday window, reconcile the live client with [its project notes](../gluetun-qbittorrent/README.md#storage-and-seeding-policy). Keep active only torrents that still need downloads or seeding; pause completed torrents once their applicable ratio or tracker requirement is met. Do not apply one global stop ratio to private-tracker torrents until their individual rules are checked. Leave the resume-data interval and disk-cache defaults unchanged unless measured I/O shows a problem: longer resume intervals trade fewer small writes for more lost client state after an unclean stop, and cache changes affect memory and I/O behavior rather than replacing a power-off schedule.

This plan intentionally keeps torrent downloading/seeding out of the Saturday SMART-test and Sunday backup windows. The documented boot task starts the Gluetun stack when OK040 boots, so the rollout must either suppress qBittorrent during maintenance or pause its torrents before the backup and test work; keep the existing VPN kill switch intact whenever qBittorrent is active.

**Rollout order:** verify enabled daily jobs; confirm OK035's Sunday power-on window; set and observe the proposed schedules for four Sundays; then review actual completion times and adjust the margins. Do not report the plan as active until the DSM and Hyper Backup settings are changed and read back.

The installed `Volition Daily Copy` helper is `/usr/local/libexec/volition/backup-notes.py` (root-owned, mode 0755). The enabled Task Scheduler entry runs it as `joost` every day at 02:00. It serializes with MCP writes, copies the full notes store including `.git`, publishes a timestamped snapshot under `/volume1/homes/joost/Volition-backups/`, and keeps the eight newest. At the 2026-10-19 check, the last successful run was 2026-10-18 22:27 and the next trigger was 2026-10-20 02:00.

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

### Mac project backups (convention, 2026-10-23)

Private runtime data of projects on the Mac (databases, credentials-adjacent state) is backed up to the NAS with one convention for every project. The first user is the LinkedIn archive (`~/Code/Linkedin`, plan in its `docs/data-layout-migration-plan.md`).

- **Where:** `/volume1/backup/<project>/YYYY-MM-DD/` (on the Mac, the `backup` share mounted over SMB). The `backup` share is a Btrfs shared folder whose DSM permissions (read on 2026-10-23) are Read/Write for `joost` and `master` only, No Access for every other account. The filesystem mode shows `rwxrwxrwx+`, but DSM's share permissions are what SMB access honours. It also holds `icloud-photo-backup` (about 75 GB, owned by `master`); each project uses its own subfolder, so nothing is mixed. `homes` is not used, because it holds personal files.
- **How the Mac reaches it:** the existing SMB mount, not SSH. The Mac LaunchAgent `com.timemachine.autosmb` (`~/bin/home-timemachine-share.sh`, every 60 s, at login and on network changes) mounts shares over Tailscale as `joost`, with the password in the login keychain. It now keeps `home` and `backup` mounted (the script was renamed on 2026-10-23 from `home-timemachine-share.sh` / `com.timemachine.autosmb` to `nas-mounts.sh` / `nl.okkinga.nas-mounts`, because the old name suggested it was part of Time Machine; the `timemachine` share was dropped from its list because mounting it as `joost` had stopped working. Time Machine itself connects separately as `master` and is unaffected). The old files are kept as `*.replaced-20261023`/`.bak`. Troubleshooting: if every SMB mount hangs at "Connecting…" while `smbutil view -N //joost@100.126.55.95` works, the macOS helper `NetAuthSysAgent` is stuck (it had run for 5 days 19 hours); `killall NetAuthSysAgent` fixed it. The mountpoint is not stable: macOS appends a suffix when a stale `/Volumes/<share>` exists (the home share was `/Volumes/home-1` on 2026-10-23; the backup share mounts as `/Volumes/backup`), so jobs must find the mount by its URL (`//joost@100.126.55.95/backup`), not by path.
- **Job rules:** a backup job never mounts anything; if the share is absent it records "deferred" and retries on the next hourly check. It copies under a temporary name, verifies by SHA-256 against the local copy, then renames. SQLite files are never opened over SMB.
- **Cadence:** weekly, by a catch-up job that runs the first time the laptop is awake after 7 days (the laptop sleeps at night). Retention 8 weekly and 12 monthly copies; the irreplaceable LinkedIn changelog copies monthly indefinitely. Same idea as the NAS's own `Volition-backups` (newest 8).
- **Off-site:** nothing new to configure. The `Timemachine Homes` Hyper Backup task already includes `/backup`, so the project folders reach OK035 on Sundays with up to 25 versions. Same caveats as above: OK035 stores the data **unencrypted** (the owner accepted this for the LinkedIn project backups on 2026-10-23; the NAS-wide decision remains open) and a restore has never been tested.
- **Snapshots:** Snapshot Replication was installed on 2026-10-23. The `backup` share has a daily schedule (01:00; smart retention); other shares have none. A manual snapshot taken at 19:30 the same day appeared as the Btrfs snapshot `@sharesnap/backup/GMT+02-2026.10.23-19.30.48` and contained the first `linkedin-archive` backup. Snapshots are not visible to SMB users. Note: `synopkg status SnapshotReplication` reported "stopped" (status 263) throughout while the package was in fact running; do not use it as evidence, look for snapshot subvolumes instead (`sudo btrfs subvolume list -s /volume1`).
- **First backup (2026-10-23):** pushed by hand to `backup/linkedin-archive/2026-10-23T172857Z/` and restored from the NAS copy into a scratch folder; checksums and database integrity verified, row counts matched the live database. **Not yet verified:** that a launchd-run job may write to the network volume (macOS can silently deny background interpreters access to network volumes). Observe the first scheduled run.

## Web Station homepage

`/volume1/web/index.html` is a static page served by Web Station on port 80, with a live status section fed by `status.json`. The source is in [status-page](../status-page/).

## Plex

Plex Media Server runs as a DSM package, not a container, with libraries on `/volume1/video` and `/volume1/audio`. Its configuration lives in the `PlexMediaServer` share and is not captured here.

## Containers that exist on the NAS

17 containers total: 16 in 6 Compose projects plus one GUI-created container (the Tailscale gateway).

| Project | Containers | Folder in this repo |
|---|---|---|
| `gluetun-qbittorrent` | gluetun, qbittorrent, prowlarr, sonarr, radarr, bazarr, lazylibrarian | [gluetun-qbittorrent](../gluetun-qbittorrent/) |
| `calibre-web` | calibre-web | [calibre-web](../calibre-web/) |
| `immich` | immich_server, immich_machine_learning, immich_postgres, immich_redis | [immich](../immich/) |
| `jellyfin` | jellyfin | [jellyfin](../jellyfin/) |
| `volition` | volition, volition-tunnel-client | [volition](../volition/) |
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
| 8766 | docker-proxy | `100.126.55.95` | Volition MCP, Tailscale only; tunnel client has no published port |
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

Installed DSM packages not described elsewhere in this repo: **ScsiTarget** (iSCSI), **Hybrid Share**, **USB Copy**, **Migration Assistant**, **QuickConnect** (switched off). Active Backup is not installed. Snapshot Replication was installed on 2026-10-23 and is running with a schedule on the `backup` share only (see Mac project backups). **ScsiTarget has no targets and no LUNs**, so it is unused.

## Power schedule

DSM's Task Scheduler lists two power tasks, `PowerOff` and `PowerOn task 0`, both **disabled** (seen in the UI on 2026-10-05). The NAS therefore runs around the clock.

## Automation outside Docker

Things that run on the NAS but are not Compose projects. None of these files are in this repo.

| What | Where | State (see dates in each entry) |
|---|---|---|
| **Volition recovery watcher** | `~/volition-deploy/` (`deploy.sh`, `install-recovery.sh`, `volition-recover-watch.sh`, `recover-tailscale-bind.sh`); installed as `/etc/systemd/system/volition-recover.service` with `/usr/local/libexec/volition/` | Volition binds to the Tailscale address, which only exists once the Tailscale container is up; this watcher listens for that container and retries Volition after the address appears. Check with `systemctl is-active volition-recover.service` (details checked 2026-10-19). |
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
- [ ] Find a supported way to verify SMART self-test completion: Task Scheduler only records the asynchronous test launch, and the drive does not support self-test logging.
- [ ] Decide whether to add a USB drive (second physical copy) or a second internal disk.
- [ ] Decide on encryption for the OK035 backups, and test a restore once.
- [ ] Configure DSM notifications so a failed backup is seen.
- [ ] Review the snapshot retention for the `backup` share (daily at 01:00, smart retention: 1 day all, 7 daily, 2 weekly, 1 monthly) and consider scheduling other shares.
- [ ] Observe the first scheduled Mac project backup writing to the SMB mount (macOS network-volume access for background jobs).

## Rebuild order

1. Install DSM 7.4, create the volume, then the users and shared folders above with the same UIDs.
2. Install Container Manager, Web Station, Hyper Backup, Plex.
3. Restore `/volume1/docker` from backup if it exists. Otherwise recreate each project from this repo and the per-project README. For Volition, use the redacted deployment references in this repo and restore the active deployment directory, `/volume1/homes/master/volition-deploy`, from the `Timemachine Homes` backup. The checked-in tunnel config and environment file are examples with redactions/placeholders; restore the active config and credentials from the backup or password manager before starting it.
4. Start [tailscale-gateway](../tailscale-gateway/) first (everything else is reached over it), then the projects in any order: gluetun-qbittorrent, immich, calibre-web, jellyfin, volition, watchtower.
5. Recreate the Task Scheduler entries, then [status-page](../status-page/).
6. Re-enter secrets from your password manager; none are in this repo.

## Secrets (names only; values are not stored here)

| Where | Names |
|---|---|
| `/volume1/docker/gluetun/.env` | `WIREGUARD_PRIVATE_KEY`, `WIREGUARD_PRESHARED_KEY`, `WIREGUARD_ADDRESSES`, `NORDVPN_WIREGUARD_PRIVATE_KEY` |
| `/volume1/docker/immich/.env` | `DB_PASSWORD` |
| `/volume1/homes/master/volition-deploy/secrets/` | `volition-authorization`, `openai-runtime-key` |
| Tailscale gateway container | `TS_AUTHKEY` |
| Watchtower compose | ntfy topic name (treated as private) |
| `/volume1/docker/lazylibrarian/config/kindle-check.conf` | `NTFY_URL` (the same ntfy topic); git-ignored, mode 640 |
| Calibre-Web (Admin → Email Server Settings) | Infomaniak device password "Calibre-Web" for sending to the Kindle |
| Each app's own UI | admin logins for qBittorrent, Prowlarr, Sonarr, LazyLibrarian, Calibre-Web, Jellyfin, Immich |
