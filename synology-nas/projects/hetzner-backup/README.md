---
title: "Hetzner backup pull"
created: "2026-11-15"
created_by: "Claude Code (Opus 5.5), at the owner's request"
creation_reason: "Hetzner TODO item 1: the production VPS had no data backups."
purpose: "Design, decisions, installation and restore of the nightly Hetzner database backup that OK040 fetches."
provenance:
  type: original
  description: "Written with the code it describes. The design was chosen with the owner on 2026-11-14 and 2026-11-15, after independent QA and security reviews of a first, rsync-based version."
  sources:
    - reference: "../../../hetzner/ansible/roles/backup/"
      description: "The Hetzner side: dump script, forced command, alert and watch scripts, systemd units."
    - reference: "pull-hetzner-backup.py"
      description: "The NAS side."
ai:
  involvement: drafting
  description: "Claude drafted the design, code and procedures; the owner made every decision listed under Decisions. Codex recorded the install and isolated restore evidence."
updated: "2026-11-15"
updated_by: "Codex"
update_reason: "Recorded installation evidence and the successful isolated restore trial."
---

# Hetzner backup pull

Every night OK040 fetches the database backups of the Hetzner platform (`ubuntu-4gb-hel1-1`) over Tailscale and keeps them in the project backup folder `/volume1/backup/hetzner/`.

**Status: installed and running since 2026-11-15; isolated restore trial completed successfully on 2026-11-15.** The NAS pull reported success at 10:12 local, fetched one copy, and selected newest stamp `2026-11-15T091239Z`, containing `db-backup_trial.dump` and `globals.sql`. Transfer checksum verification succeeded. The trial restored 1,000 deterministic rows in a `postgres:18.7` container with `network=none`; production and restored row-set SHA-256 values both were `182ecb1e65491145dc95a975f95ae6621679ed4a3a1354c05a76710475ac77db`. The database and role count returned to zero, the container was removed, and `/home/joost/restore` was absent afterward. The trial-created copy remains in the NAS retention set. Full evidence is in [Hetzner operations](../../../hetzner/ubuntu-4gb-hel1-1/operations.md#isolated-restore-trial-15-november-2026).

## How it works

| When | Where | What |
|---|---|---|
| 01:30 | Hetzner, `platform-backup.timer` | Dumps `globals.sql` (roles, without password hashes) and one `db-<name>.dump` per database (`pg_dump -Fc`, read back in full before it counts) into `/srv/backup/<UTC timestamp>/` with `SHA256SUMS`. Publishes by atomic rename; keeps the newest 7. Fails if a database in `platform_apps` is missing or less than 2 GB is free. A failure sends an ntfy alert. |
| 07:30 | OK040, Task Scheduler task "Hetzner backup pull", user `hetznerbackup` | [`pull-hetzner-backup.py`](pull-hetzner-backup.py) asks the server for its list, fetches each backup it does not hold yet, checks every checksum, and publishes it read-only in `/volume1/backup/hetzner/copies/<timestamp>/`. It only fetches backups newer than its newest copy, at most 8 per run. It then re-checks all held copies, keeps 7 daily and the newest of 4 ISO weeks (the current week counts as one, so the oldest copy is about three weeks old), and tells the server `done`. Any failure sends an ntfy alert and is written to `/volume1/backup/hetzner/status/last-run.json`. |
| 10:00 | Hetzner, `platform-backup-watch.timer` | Alerts if OK040 has not confirmed a pull for 26 hours: the NAS off, its task disabled or hung. |
| With each status refresh | OK040 status page | "Hetzner backup" row: green while the last success is under 26 hours old. |
| 01:00 daily / Sundays | OK040 / OK035 | The existing daily snapshot of the `backup` share and the Sunday Hyper Backup to OK035 (Timemachine Homes, which includes `/backup`) cover these copies too. |

**What the NAS key can do.** On the Hetzner server, account `nasbackup` (no password) accepts one key, only from OK040's Tailscale address (`from=` in `authorized_keys` and `AllowUsers nasbackup@100.126.55.95`), with `restrict` and the forced command `/usr/local/lib/platform-backup/backup-serve`. That command understands only:

- `list`: the published backup names;
- `get <stamp> <file>`: the bytes of one regular file, with both names checked against strict patterns and symlinks refused;
- `done <stamp>`: the NAS's confirmation, read by the 10:00 watch.

Everything else is refused and logged (`journalctl -t backup-serve`).

**What a hacked Hetzner server can and cannot do.** It can stop producing backups, or send bad *new* ones (up to 8 a night, each within the size caps and a free-space floor); the older verified copies, the share snapshots and the OK035 versions remain. It cannot write outside the files the NAS script creates, cannot overwrite or change a copy the NAS already holds, cannot slip in backdated or future-dated backups, and cannot open any connection to the NAS. Output beyond the size limits ends the call at once, so a flood cannot exhaust the NAS's memory or disk. The tailnet has no rule from `tag:hetzner-prod` to anything.

**Files on OK040**

| Path | Owner, mode | What |
|---|---|---|
| `/usr/local/libexec/hetzner-backup/pull-hetzner-backup.py` | root 0755 | Copy of the script in this folder |
| `/usr/local/etc/hetzner-backup/` | root:hetznerbackup 0750 | Configuration folder; the job can read, not change it |
| `.../hetzner-backup.conf` | root:hetznerbackup 0640 | From [`hetzner-backup.conf.example`](hetzner-backup.conf.example); holds the ntfy topic URL |
| `.../id_ed25519` | hetznerbackup 0600 | Pull key (private half) |
| `.../known_hosts` | root 0644 | Hetzner host key, `SHA256:DeixvRwYazTkhYE0lg3k30m9f8C3efUKmbBDcwYwvTc` |
| `/volume1/backup/hetzner/` | DSM permissions: `hetznerbackup` read/write here, traverse only on the `backup` share root | The job cannot change other projects in the share (LinkedIn, iCloud photos). `joost` and `master` keep their share access; a change they make to a copy is caught by the nightly re-check. |
| `/volume1/backup/hetzner/copies/` | hetznerbackup; folders 0500, files 0400 | The copies |
| `/volume1/backup/hetzner/status/` | hetznerbackup | `last-run.json` (read by the status page) and the run lock |

## Decisions

| Date | Decision | Why | Rejected |
|---|---|---|---|
| 2026-11-14 | OK040 **pulls**; the Hetzner server gets no access to the NAS. | A hacked server must not be able to delete or reach the backups. | Server pushes to the NAS. |
| 2026-11-14 | A small script, not Active Backup for Business or restic. | Active Backup is not installed, keeps its settings outside Git, and its SSH-key support is uncertain. Restic adds a tool for one small database. | Active Backup for Business; restic. |
| 2026-11-15 | **No rsync on the NAS.** The server offers only `list`, `get` and `done`; the NAS names every file itself. | The independent security review found that a root rsync client lets a hostile server plant symlinks, overwrite held copies and silence alerts. DSM ships rsync 3.1.2, which has known client-side holes (CVE-2024-12086/12087/12088), and DSM's copy cannot be upgraded. | Upgrade rsync (not possible for DSM's copy; Entware is unmanaged); rsync in a container (owner preferred no extra container). |
| 2026-11-15 | The pull runs as the unprivileged DSM user `hetznerbackup`, writing only to `/backup/hetzner/` (read/write there, traverse only on the share root). | Keeps one `backup` share with one snapshot schedule and one Hyper Backup source, following the `backup/<project>/` convention. The script names every file itself, so a hacked server cannot direct writes elsewhere; the folder permission also contains a bug in the script. Changes by `joost`/`master` are caught by the nightly re-check. If DSM cannot set traverse-only, read/write on the whole share is acceptable for the same reasons. | Running as root; a separate `hetzner-backup` share (more to manage). |
| 2026-11-15 | The NAS fetches only backups newer than its newest copy, at most 8 per run. | A hacked server could otherwise send backdated backups that push genuine weekly copies out, or fill the disk. | Fetching every unknown name. |
| 2026-11-15 | **Caddy data is not backed up.** | It holds the TLS private keys and ACME account key; Caddy obtains new certificates by itself. | Backing it up, with or without encryption. |
| 2026-11-15 | **Database dumps are stored unencrypted** on OK040 (and on OK035 until that copy is encrypted; see the NAS TODO). | Today no app holds data. Readers are the same as for the rest of the NAS: `joost` and `master`, NAS root, disk theft. **Revisit before an app stores other people's personal data**; then encrypt on the server with `age`, private key in Proton Pass. | Encryption at source now. |
| 2026-11-15 | Three ways to notice failure: NAS ntfy alert, Hetzner-side ntfy alert when no pull is confirmed for 26 hours, status page row. | An alert only fires from a job that runs; the second machine covers the first being down. | External heartbeat service. |
| 2026-11-15 | The Hetzner server uses its **own** ntfy topic. | It is the internet-facing machine; if it is hacked, the NAS's topic stays private. | Sharing the NAS topic. |
| 2026-11-15 | Dump at 01:30 local time, pull at 07:30. | 02:00-03:00 is skipped on the spring daylight-saving night. OK040 is powered off on weekdays from 00:15 to 07:00 (DSM tasks "PowerOff task 0" / "PowerOn task 0"), so the pull runs after power-on and before the 10:00 watch. | Dump at 02:30; pull at 03:00 (the NAS is off then on weekdays). |

## Install

Each step needs the owner's go-ahead. Steps 1, 2, 5 and 6 change OK040; step 4 changes the live Hetzner server. Do steps 4 and 5 on the same day, or the 10:00 watch alerts that the NAS never confirmed a pull.

1. **OK040, DSM:**
   - Create user `hetznerbackup`: not an administrator, a random password (it never logs in interactively), all applications denied, no access to any existing share.
   - File Station: create folder `backup/hetzner`. On the `backup` share root (Properties → Permission), give `hetznerbackup` **Traverse folders/Execute files** and **List folders** for "this folder only". On `backup/hetzner`, give it read/write for "this folder, child folders and files".
   - Snapshots and the off-site copy need nothing new: the `backup` share already has both.
2. **OK040, SSH:**
   DSM gives a new user no group of its own, so create one first (only `hetznerbackup` in it), so the configuration is readable by the job and nobody else:
   ```sh
   sudo /usr/syno/sbin/synogroup --add hetznerbackup hetznerbackup
   sudo install -d -o root -g hetznerbackup -m 0750 /usr/local/etc/hetzner-backup
   sudo install -d -o root -g root -m 0755 /usr/local/libexec/hetzner-backup
   sudo install -d -o hetznerbackup -m 0700 /volume1/backup/hetzner/copies
   sudo install -d -o hetznerbackup -m 0755 /volume1/backup/hetzner/status
   sudo ssh-keygen -t ed25519 -N "" -C ok040-hetzner-backup -f /usr/local/etc/hetzner-backup/id_ed25519
   sudo chown hetznerbackup /usr/local/etc/hetzner-backup/id_ed25519
   ```
   DSM has no `ssh-keyscan`. Pin the host key from the Mac, after checking it against the fingerprint above:
   ```sh
   K=$(ssh joost@ubuntu-4gb-hel1-1.tail4d7938.ts.net 'cat /etc/ssh/ssh_host_ed25519_key.pub' | awk '{print $1" "$2}')
   echo "$K" | ssh-keygen -lf -   # must show the fingerprint above
   echo "100.105.28.57 $K" | ssh ok040 'sudo tee /usr/local/etc/hetzner-backup/known_hosts'
   ```
   Install the script (root 0755) and the config (root:hetznerbackup 0640, ntfy URL from the Watchtower Compose file). Check the permissions: as `hetznerbackup`, writing in `/volume1/backup/linkedin-archive` must fail and writing in `/volume1/backup/hetzner` must work (`sudo -u hetznerbackup touch …`).
3. **ntfy:** create a second private topic for the Hetzner server and subscribe to it on the phone.
4. **Hetzner:** put the public key (`id_ed25519.pub`) in `backup_nas_public_key` in `hetzner/ansible/group_vars/all.yml`. Run `BACKUP_NTFY_URL=https://ntfy.sh/<hetzner topic> ansible-playbook site.yml --tags ssh,backup --check --diff`, review, then apply, and rerun to see `changed=0`. Then `sudo systemctl start platform-backup`, `journalctl -u platform-backup`, and a test alert: `sudo /usr/local/lib/platform-backup/backup-alert test`.
5. **OK040:** run the job once by hand as its user: `sudo -u hetznerbackup python3 /usr/local/libexec/hetzner-backup/pull-hetzner-backup.py`, and send one test alert to the NAS topic. Check the refusals: `sudo -u hetznerbackup ssh -F /dev/null -i /usr/local/etc/hetzner-backup/id_ed25519 -o UserKnownHostsFile=/usr/local/etc/hetzner-backup/known_hosts nasbackup@100.105.28.57 'cat /etc/passwd'` must print `refused`, as must `get <stamp> ../x`.
6. **DSM:** Control Panel → Task Scheduler → Create → Scheduled Task → User-defined script: task "Hetzner backup pull", user `hetznerbackup`, daily 07:30 (the NAS is off 00:15-07:00 on weekdays), command `/usr/bin/python3 /usr/local/libexec/hetzner-backup/pull-hetzner-backup.py`. Deploy the [status page](../status-page/) change.
7. **Restore trial** (below), then record the evidence in `hetzner/ubuntu-4gb-hel1-1/operations.md`.

## When a held copy fails its check

The job then stops pruning and confirming, and both sides alert every night. Look at the copy first: a change made on the NAS points to a problem there, not on the server. To remove it:

```sh
sudo chmod -R u+w /volume1/backup/hetzner/copies/<stamp>
sudo mv /volume1/backup/hetzner/copies/<stamp> /volume1/backup/hetzner/quarantine-<stamp>   # or rm -r
```

## Restore

Restore from a copy taken **before** any suspected compromise of the server. Treat a dump as untrusted input until it has been opened in a throwaway container.

1. **Get the copy onto the target.** The server cannot reach the NAS, so stream it from the Mac:
   ```sh
   ssh ok040 'sudo tar -C /volume1/backup/hetzner/copies -cf - <stamp>' | ssh joost@ubuntu-4gb-hel1-1.tail4d7938.ts.net 'mkdir -p ~/restore && tar -C ~/restore -xf -'
   ```
   On the target: `cd ~/restore/<stamp> && chmod -R u+w . && sha256sum -c SHA256SUMS`.
2. **Platform:** rebuild or reuse it with Ansible. That recreates the roles, passwords and empty databases for every app in `platform_apps`. A rebuilt server has a new host key and possibly a new Tailscale address: update `known_hosts` and `host` on OK040.
3. **Each app**, with the app stopped:
   ```sh
   cd /tmp   # /srv/platform is root-only; pass it with --project-directory
   sudo docker compose --project-directory /srv/platform cp ~/restore/<stamp>/db-<app>.dump postgres:/tmp/restore.dump
   sudo docker compose --project-directory /srv/platform exec -T postgres pg_restore -h 127.0.0.1 -U <app> -d <app> --clean --if-exists --no-owner --exit-on-error --single-transaction /tmp/restore.dump
   sudo docker compose --project-directory /srv/platform exec -T postgres rm /tmp/restore.dump
   ```
   Connect **as the app role**, not as `postgres`, so a crafted dump cannot run superuser commands. Inside the container, loopback connections are trusted (`pg_hba.conf`), so no password is asked. If the dump needs an extension the app role may not create, the restore stops with an error and changes nothing; create the extension as `postgres` first, after checking the dump's listing (`pg_restore -l`). Then start the app.
4. `globals.sql` lists roles that Ansible does not manage. **Read it; never run it through `psql`**: it comes from a server that may have been compromised. It contains no passwords.
5. **Caddy** needs nothing: it obtains new certificates once DNS points at the server.

**Trial:** do step 1 into a scratch folder, start a throwaway `postgres:18.7` container, create the role and database (`createuser <app>`, `createdb -O <app> <app>`), restore as in step 3, and compare row counts with production. Remove the container afterwards.
