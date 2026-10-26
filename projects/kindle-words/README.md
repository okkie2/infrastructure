# kindle-words

Learn the words looked up on the Kindle. A jailbroken Kindle Paperwhite 5 uploads its Vocabulary Builder database over Wi-Fi; this container stores it and serves a small web app with a word list and flashcard study (Anki-style SM-2 scheduling, Wiktionary definitions, browser pronunciation). It works on phone and desktop.

The source code, the Kindle scripts and the jailbreak notes live in the **`kibble` repository** (`~/Code/kibble`, formerly `kindle`), which is canonical; this folder records how it runs on OK040. Deployed on 2026-10-25.

| Item | Value |
|---|---|
| Container | `kindle-vocab` in `/volume1/docker/kindle-vocab`, started with `docker-compose` over SSH (not registered in Container Manager) |
| Image | `python:3.12-alpine` pinned by digest; stdlib only, no build. Not in Watchtower's list; update by changing the digest. |
| Compose file | [`docker-compose.yml`](docker-compose.yml), a copy of `kindle/app/docker-compose.yml` |
| App code | `/volume1/docker/kindle-vocab/app` (mounted read-only at `/app`), copied from `kindle/app/` |
| Port | `8770` on all interfaces: http://192.168.178.110:8770/ (LAN), http://100.126.55.95:8770/ (Tailscale) |
| Runs as | uid 1026 (`master`), gid 100; read-only root, `cap_drop: ALL`, `no-new-privileges`, 256 MB, 64 processes |
| Data | `/volume1/docker/kindle-vocab/data` (see below) |
| Secret | `SYNC_TOKEN` in `/volume1/docker/kindle-vocab/.env` (mode 600); the same value is on the Kindle in `/var/local/vocab-sync/config` |
| Secret | `MW_KEY` (Merriam-Webster Collegiate API key, free non-commercial) in the same `.env`; optional, without it definitions come from Wiktionary only |
| Secret | Tailscale login of node `kb-bnjx` (tag:kibble, service `kindle-vocab-ts`, HTTPS for the iPhone app) in `/volume1/docker/kindle-vocab/tailscale` (root, 700); re-enrol with a single-use `TS_AUTHKEY`, see the kindle repo README "iPhone app" |
| Logs | `sudo /usr/local/bin/docker logs kindle-vocab` |

## Data

| Path in `data/` | What | Backed up |
|---|---|---|
| `vocab.db` | Latest raw upload from the Kindle | Media Docker (weekly) |
| `words.db` | Validated copy the app reads, rebuilt on every upload | Media Docker |
| `history/` | The last 30 uploads | Media Docker |
| `study.db` | Study progress, review log, cached definitions. **Only here**; the Kindle does not have it. | Media Docker |

The Kindle remains the source of truth for the words themselves. Up to a week of study progress can be lost between Sunday backups.

## How the Kindle reaches it

The Kindle runs a root cron job every 30 minutes (only while awake) that syncs at most once a day: it copies `vocab.db` with `sqlite3 .backup` and POSTs it to `http://192.168.178.110:8770/upload` with the bearer token. Sync only works on the home Wi-Fi; the Kindle has no Tailscale. Details: `kindle/README.md` and `kindle/docs/jailbreak.md`.

## Security

- Only `POST /upload` needs the token. The web app and its API (`/api/words`, `/api/study`, `/api/define`, `/api/review`) have **no login**; they rely on the NAS being reachable only from the LAN and Tailscale (no router forwards, QuickConnect off).
- Requests must carry a known `Host` header (`ALLOWED_HOSTS` in the Compose file) and POSTs a matching `Origin`, which blocks DNS rebinding. Uploads are validated before use (no views, triggers or virtual tables, `quick_check`, a 10-second query limit) and an upload with less than half the current word count is refused (HTTP 409).
- The port binds to all interfaces, not the Tailscale address, because a Tailscale-only bind fails when Docker starts before the Tailscale container after a reboot (Volition needs a recovery watcher for the same reason). The NAS has no public IPv6 on `eth0`.
- Outbound: the container fetches definitions from `en.wiktionary.org`.
- QA and security reviews on 2026-10-25: both conditionally ready. The open conditions (on-device checks, token rotation, a reboot test) are in `kindle/TODO.md`.

## Deploy or update

From the `kindle` repository:

```sh
cd app
for f in server.py study.py dictionary.py vocab.py index.html; do
  ssh ok040 "cat > /volume1/docker/kindle-vocab/app/$f" < $f
done
ssh ok040 "cat > /volume1/docker/kindle-vocab/docker-compose.yml" < docker-compose.yml
ssh ok040 'cd /volume1/docker/kindle-vocab && sudo /usr/local/bin/docker-compose up -d --force-recreate'
```

Then copy the Compose file here too, so this folder matches.

## Rebuild

1. Restore `/volume1/docker/kindle-vocab` from the Media Docker backup. If that is not possible, create `app/` and `data/`, deploy as above, and let the Kindle sync again (study progress is lost without `study.db`).
2. Create `.env` with `SYNC_TOKEN=<value>` (mode 600). Use the value from the Kindle's `/var/local/vocab-sync/config`, or generate a new one (`openssl rand -hex 20`) and reinstall the Kindle config.
3. `sudo /usr/local/bin/docker-compose up -d` and check `curl http://192.168.178.110:8770/health`.
