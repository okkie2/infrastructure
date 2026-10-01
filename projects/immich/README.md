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

Confirm that `/volume1/docker/immich` is in a Hyper Backup source ([host](../host/)); it is not documented anywhere that it is.
