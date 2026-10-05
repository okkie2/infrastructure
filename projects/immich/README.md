# immich

Photo management for the NAS. Four containers in one Compose project, started with `docker compose` over SSH (not through the Container Manager wizard, so the UI's Build button does not apply).

| Container | Image | Role |
|---|---|---|
| `immich_server` | `ghcr.io/immich-app/immich-server:v3.1.0` | Web UI and API on port `2283` |
| `immich_machine_learning` | `ghcr.io/immich-app/immich-machine-learning:v3.1.0` | Face and search models, cache in the named volume `immich_model-cache` |
| `immich_postgres` | `ghcr.io/immich-app/postgres:14-vectorchord0.4.3-pgvectors0.2.0@sha256:…` | Database with the vector extensions Immich needs |
| `immich_redis` | `valkey/valkey:9@sha256:…` | Cache / queue |

Files: [`docker-compose.yml`](docker-compose.yml) (a faithful copy of the NAS file) and [`.env.example`](.env.example). The NAS folder also holds `hwaccel.ml.yml` and `hwaccel.transcoding.yml`, which are Immich's stock files and are unused (hardware acceleration is off); get fresh copies from the Immich release if wanted.

## Where things live

| What | Path |
|---|---|
| Compose project | `/volume1/docker/immich` |
| Uploads and generated media (`UPLOAD_LOCATION`) | `/volume1/docker/immich/library` |
| Database files (`DB_DATA_LOCATION`, must be local disk) | `/volume1/docker/immich/postgres` (owner uid 999, mode 700) |
| Existing photo archive | `/volume1/photo`, mounted read-only at `/mnt/media/photo`; added in the UI as an External Library with that path |
| Secrets | `/volume1/docker/immich/.env` (mode 600): `DB_PASSWORD` |

## Decisions worth knowing

- **Version is pinned** (`IMMICH_VERSION=v3.1.0`). Database migrations are one-way, so never float the tag. Upgrade by reading the release notes, changing the version in `.env`, then `sudo docker compose pull && sudo docker compose up -d`. Take a database dump first.
- All four containers carry the label `com.centurylinklabs.watchtower.monitor-only=true`: [watchtower](../watchtower/) reports on them but never updates them.
- `DB_STORAGE_TYPE: HDD` is set for the DS225+'s spinning disks. `--data-checksums` is on for the database.
- Transcoding is CPU only (the hardware-acceleration `extends:` lines are commented out).
- Compose project name is `immich` (set by `name: immich`).

## Rebuild

```sh
ssh ok040 'mkdir -p /volume1/docker/immich/library /volume1/docker/immich/postgres'
ssh ok040 'cat > /volume1/docker/immich/docker-compose.yml' < projects/immich/docker-compose.yml
# create /volume1/docker/immich/.env from projects/immich/.env.example with a real DB_PASSWORD, chmod 600
ssh ok040 'cd /volume1/docker/immich && sudo docker compose up -d'
```

Restoring an existing instance needs the `library` folder **and** the `postgres` folder from the same moment (or a database dump that matches the library). Restoring only one gives broken or missing photos. The Immich mobile app server URL is `http://100.126.55.95:2283`; log in as the admin you created, then add the external library.

## Backups

State on 2026-10-05:

- Immich writes its own **database dump every night at 02:00** into `library/backups/` (`immich-db-backup-<timestamp>-v3.1.0-pg14.19.sql.gz`, about 162 MB each). 14 are kept (2.2 GB, 2026-09-22 to 2026-10-05). I did not check the setting that controls how many are kept.
- `/volume1/docker` (library, dumps and the raw `postgres` data directory) is in the Hyper Backup task **Media Docker** → OK035 share `Backup C`, **weekly on Sundays at 12:15**. The external archive `/volume1/photo` is in the same task. See [host → Backups](../host/#backups).

Gaps:

1. **OK035 is only up on Sundays**, so the weekly run is the only off-disk copy and up to 7 days of newly uploaded photos exist only on the NAS.
2. **OK040 has a single drive** (see [host](../host/#hardware-and-os)): every other copy on the NAS is on the same disk, so it protects against deleted or damaged files but not against a disk failure.
3. The live `postgres` data directory is copied as plain files while the database runs; such a copy may not restore cleanly. The dumps are the reliable copy.
4. The off-site copy is stored unencrypted, on a single machine, and no restore has ever been tried. A failed backup produces no visible alert.

Plan (owner's direction, 2026-10-05; **not yet applied**):

- Add a **daily Hyper Backup task on OK040** (for example 03:30, after the 02:00 dump) that copies `/docker/immich/library` (including `backups/`) into a local folder under `/volume1/backup/`, keeping about 14 versions. The existing weekly task **Timemachine Homes already includes `/backup`**, so the Sunday run carries the daily copy to OK035 (share `Backup D`) with no new remote task. Cost: roughly 120 GB more on OK035, because Media Docker also copies the Immich library.
- **Exclude `/docker/immich/postgres`** from the local task (and consider it for Media Docker) and rely on the dumps.
- Because the daily copy is on the same disk, add a **second physical copy** when affordable: a USB drive as a Hyper Backup target (daily), or a second internal disk for RAID1 (RAID is not a backup).
- Optionally an **encrypted cloud copy** of the library and dumps (about 119 GB) for the days OK035 is off.
- **Test one restore**: start a scratch Immich of the same pinned version, restore a dump following Immich's documentation, and compare photo counts; repeat after each Immich upgrade.
- **Make failures visible**: configure DSM notifications or have the backup tasks call ntfy (see [host → Notifications](../host/#notifications-ntfy)).
