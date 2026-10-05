# synology-nas

Configuration and notes for running **qBittorrent**, **Prowlarr**, and **Sonarr** on a Synology DS225+ (DSM 7.4, Container Manager). Torrent traffic goes through a VPN and **stops completely if the VPN fails**; Sonarr manages the existing TV library.

```
qBittorrent ──► Gluetun ──► WireGuard ──► AirVPN (Netherlands) ──► Internet
                  ▲
Prowlarr ─────────┘  (talks to qBittorrent's Web UI at gluetun:8080; itself not behind the VPN)
Sonarr (8989) ───────► /tv (existing Plex TV library)
```

It is written for one household NAS, not as a reusable product. The repo holds the Compose project, a kill-switch test and the working notes; the containers and their data live on the NAS.

## What you get

- **Kill switch.** qBittorrent has no network of its own (`network_mode: "service:gluetun"`). With the tunnel down, or Gluetun stopped, it can reach nothing. `projects/gluetun-qbittorrent/scripts/kill-switch-test.sh` proves it.
- **Inbound peers.** AirVPN forwards one fixed port (see [Configuration](#configuration)) to qBittorrent, so seeding works.
- **Web UIs.** qBittorrent on port 8080 and Prowlarr on 9696 follow the existing published-port setup. Sonarr uses the same pattern on port 8989.
- **Sonarr deployed.** Sonarr is running on port 8989, authentication is enabled, `/tv` points to the existing Plex TV folder, and qBittorrent is configured at `gluetun:8080`. A real completed-episode import and Plex pickup have not yet been verified.
- **Persistence.** Settings live in `/volume1/docker/<service>/config`; downloads go to the normal shared folder `/volume1/download/qbittorrent`. Both survive restarts and image updates.
- **Boot start.** `scripts/start-stack.sh` is run by a DSM Task Scheduler boot-up task (as root): it waits for Docker, then runs `docker compose -p gluetun-qbittorrent up -d --no-recreate`. It exists because Container Manager skipped qBittorrent after a reboot (it had exited 137). Copy it to `/volume1/docker/gluetun/start-stack.sh`; the task was not in the task list on 2026-10-01, so check that it still exists.
- **Book manager.** LazyLibrarian (port 5299) runs in the same project; see the Configuration table.
- **Fallback.** `projects/gluetun-qbittorrent/docker-compose.nordvpn.yml` is the previous NordVPN setup (no port forwarding).

## Quick start

Assumes SSH access to the NAS as `ok040` and a running Container Manager. Nothing secret is stored in this repo.

1. **Create the folders** (the `downloader` DSM user, uid 1031 / gid 100, runs the containers):

   ```sh
   ssh ok040 'mkdir -p /volume1/docker/gluetun /volume1/docker/qbittorrent/config /volume1/docker/prowlarr/config /volume1/download/qbittorrent \
     && mkdir -p /volume1/docker/sonarr/config \
     && chmod 775 /volume1/docker/gluetun /volume1/docker/qbittorrent /volume1/docker/qbittorrent/config /volume1/docker/prowlarr /volume1/docker/prowlarr/config /volume1/docker/sonarr /volume1/docker/sonarr/config /volume1/download/qbittorrent'
   ```

2. **Create the private `.env`.** In the AirVPN Client Area, use the Config Generator (WireGuard, Linux, Netherlands) and reserve a forwarded port at `https://airvpn.org/ports/` (TCP+UDP, remote = local port). Copy `.env.example` to `/volume1/docker/gluetun/.env` on the NAS, fill it in and lock it down:

   ```sh
   ssh ok040 'chmod 600 /volume1/docker/gluetun/.env'
   ```

3. **Copy the Compose file** to the NAS (the SFTP subsystem is off, so pipe it through SSH):

   ```sh
   ssh ok040 'cat > /volume1/docker/gluetun/docker-compose.yml' < projects/gluetun-qbittorrent/docker-compose.yml
   ```

4. **Create the project** in DSM: Container Manager → Project → Create. Name `gluetun-qbittorrent`, path `/docker/gluetun`, "Use existing docker-compose.yml", no web portal, start it.

5. **Check the VPN** (control server listens on the NAS only):

   ```sh
   ssh ok040 'curl -s http://127.0.0.1:8000/v1/vpn/status; echo; curl -s http://127.0.0.1:8000/v1/publicip/ip; echo; curl -s https://ipinfo.io/ip'
   ```

   The exit IP must differ from the last line (your home IP).

6. **First logins.** Read qBittorrent's temporary admin password from its container log (Container Manager → Container → `qbittorrent` → Log) and set your own; set a Forms login in Prowlarr. Then in Prowlarr add qBittorrent as a download client (`gluetun`, port 8080). Set qBittorrent's listening port to the forwarded port.

7. **Sonarr setup (partly complete).** Sonarr is deployed on port 8989. Authentication is enabled, and `/tv` is configured as the series root; the Compose mount maps `/tv` to NAS `/volume1/video/TV Shows`, the folder also mounted on a Mac as `/Volumes/video/TV Shows`. Add qBittorrent as Sonarr's download client at host `gluetun`, port `8080`, with the qBittorrent Web UI login. This lets Sonarr track downloads it manages and import completed episodes from `/downloads`. The `/downloads` path maps to the same qBittorrent downloads directory inside both containers. Prowlarr integration is optional and only needed if Sonarr will search for releases through Prowlarr. Plex is expected to scan its already-configured TV root; automatic pickup has not been verified.

## Configuration

| What | Where |
| --- | --- |
| Stack definition | `docker-compose.yml` (project `gluetun-qbittorrent`) |
| Secrets (WireGuard keys, address) | `/volume1/docker/gluetun/.env` on the NAS, mode 600; template in `.env.example` |
| Forwarded port | `FIREWALL_VPN_INPUT_PORTS` in the Compose file, and qBittorrent's listening port (`Session\Port`); both must equal the port reserved at AirVPN |
| Web UIs | qBittorrent `http://<nas>:8080`, Prowlarr `http://<nas>:9696`, Sonarr `http://<nas>:8989` (same published-port pattern as existing apps) |
| Service config | `/volume1/docker/qbittorrent/config`, `/volume1/docker/prowlarr/config`, `/volume1/docker/sonarr/config` |
| Downloads | `/volume1/download/qbittorrent` (files are group-writable: `UMASK=002`) |
| LazyLibrarian (deployed; runs as uid 1028 `calibre` for write access to the library) | `http://<nas>:5299`; config `/volume1/docker/lazylibrarian/config`; Calibre library `/books/Library` (NAS `/volume1/books/Library`); set Processing → Calibredb import program to `/usr/bin/calibredb` |
| Sonarr paths | `/downloads` for qBittorrent downloads; `/tv` for the existing `/volume1/video/TV Shows` library |

## Operating it

- **Change the Compose file or update images:** stop the project, then Action → Build (Build is greyed out while it runs). Watchtower deliberately ignores these containers.
- **Restart qBittorrent** from the project (Project → Restart), never from the Container list: Container Manager refuses to start it alone ("must join at least one network"). If Gluetun is restarted outside Compose, restart qBittorrent too, or it stays offline (the safe direction).
- **Edit `qBittorrent.conf`** only while the project is stopped: the app rewrites it on shutdown. The file is world-writable, the folder is not, so edit it in place.
- **Test the kill switch** after any VPN change (needs `sudo` on the NAS; it restores everything itself):

  ```sh
  ssh ok040 'cat > /tmp/kill-switch-test.sh' < projects/gluetun-qbittorrent/scripts/kill-switch-test.sh
  ssh -t ok040 'sudo sh /tmp/kill-switch-test.sh; rm -f /tmp/kill-switch-test.sh'
  ```

- **Fall back to NordVPN:** from the repository root, run `ssh ok040 'cat > /volume1/docker/gluetun/docker-compose.yml' < projects/gluetun-qbittorrent/docker-compose.nordvpn.yml`, set qBittorrent's listening port back to 6881 and rebuild. NordVPN offers no forwarded port, so seeding stalls.

## LazyLibrarian: from download to Calibre-Web and the Kindle

Path of a book: Prowlarr (Torznab feeds) → LazyLibrarian search → qBittorrent (category `books`) → LazyLibrarian post-processor (every 10 minutes) → `calibredb` import into `/books/Library` → [Calibre-Web](../calibre-web/) → email to the Kindle (see its README). Verified end to end on 2026-10-02 (import) and 2026-10-05 (Kindle delivery).

Things learned while running it (2026-10-02 to 2026-10-05):

- **LazyLibrarian only searches books with status `Wanted`.** Importing an author adds every edition as `Skipped` (879 of 921 books on 2026-10-02), including sheet music and translations, so mark just the titles you want as Wanted. Searching "returns no results" for the rest is expected.
- **qBittorrent's queue can silently stall.** With its default of 3 active downloads, three dead torrents (state `stalledDL`, 0 seeds) blocked every other torrent, including Sonarr's, which sat in `queuedDL` at 0%. Set on 2026-10-02 in Options → BitTorrent: max active downloads 16, uploads 8, torrents 8, and "Do not count slow torrents" ticked. Remove dead torrents by hand.
- **Audiobook releases get picked for eBooks.** LazyLibrarian rejects them ("contains audiobook files instead of ebook", status `Failed`) but does not delete a torrent it did not add itself, so the torrent stays in qBittorrent.
- **OpenLibrary is blocked for 1 hour** after a burst of author imports (about 15 lookups). `blocked_providers.json` keeps the old entry after it expires; it has no effect then.
- **The EBookBay indexer (`ebb.la`) cannot be added to Prowlarr.** The site serves a certificate for `audiobookbay.lu`, so Prowlarr reports `RemoteCertificateNameMismatch`. DNS, VPN and FlareSolverr do not fix a wrong server certificate.
- **Docker needs `sudo` over SSH:** `sudo -n /usr/local/bin/docker …` works without a password. `calibredb` and `ebook-convert` exist inside the `lazylibrarian` container (from the `universal-calibre` mod).

### Kindle EPUB check (warn-only pre-process hook)

Amazon accepted but never delivered one EPUB: *A Fire Upon the Deep* (public-tracker release) is stored as **1,581 tiny HTML files**. Calibre rebuilt it to 21 and Amazon then delivered it. LazyLibrarian can run a script on every download before import (`EXT_PREPROCESS`); [`scripts/kindle-check.py`](scripts/kindle-check.py) counts an EPUB's spine items and sends an ntfy alert (see [Notifications](../host/README.md#notifications-ntfy)) when there are more than **1,000**. It never modifies or blocks anything and always exits 0.

| Item | Value |
|---|---|
| Script on the NAS | `/volume1/docker/lazylibrarian/config/kindle-check.py` (container path `/config/kindle-check.py`), mode 755 |
| Alert target | `kindle-check.conf` next to it, mode 640, one line `NTFY_URL=https://ntfy.sh/<topic>`; template [`scripts/kindle-check.conf.example`](scripts/kindle-check.conf.example). Never committed (`*.conf` is git-ignored). |
| Log | `/volume1/docker/lazylibrarian/config/log/kindle-check.log` (one line per EPUB checked; does not rotate) |
| Enabled by | LazyLibrarian config `[General] ext_preprocess = /config/kindle-check.py` (set 2026-10-05 through LazyLibrarian's API, `cmd=writeCFG&name=EXT_PREPROCESS&group=General`, so no restart); backup `config.ini.bak-20261005-preprocess` |
| Threshold | 1,000 spine items. A guess: a 568-item omnibus delivered fine, the 1,581-item book failed. In 51 library EPUBs the median is 33 and only 5 exceed 100. Adjust `THRESHOLD` once more cases are known. |

Install:

```sh
ssh ok040 'cat > /volume1/docker/lazylibrarian/config/kindle-check.py' < projects/gluetun-qbittorrent/scripts/kindle-check.py
ssh ok040 'chmod 755 /volume1/docker/lazylibrarian/config/kindle-check.py'
# create kindle-check.conf from the example, then set the option (key from [API] in config.ini):
curl "http://<nas>:5299/api?apikey=<key>&cmd=writeCFG&name=EXT_PREPROCESS&group=General&value=/config/kindle-check.py"
```

Test: run it inside the container as LazyLibrarian's user against an EPUB folder, `sudo -n docker exec -u abc lazylibrarian /config/kindle-check.py eBook <folder> <author> <title>`. Expect a log line, and an ntfy message only above the threshold.

**To switch it off, clear the option first** (`value=` empty). If the script file is removed while the option is still set, LazyLibrarian treats the missing script as a failure and **rejects every import** ("PreProcessor returned 1").

### Rebuilding a bad EPUB (`fix-epub`, run on the Mac)

[`scripts/fix-epub`](scripts/fix-epub) is the manual cure: `fix-epub <calibre-book-id> [--dry-run]` (install it as `~/bin/fix-epub`). It fetches the book's EPUB over SSH, rebuilds it with the Mac's Calibre (EPUB → HTMLZ → EPUB with `--dont-split-on-page-breaks --chapter-mark none`, which merges the fragments), refuses to continue unless the file count drops, keeps the original in `/volume1/docker/_scratch/epub-backup/` on the NAS, and adds the rebuilt EPUB with `calibredb add_format`. It takes seconds on the Mac and minutes on the NAS, which is why it runs on the Mac. The book id is the number in the Calibre-Web URL (and in the folder name, `Title (120)`). `--dry-run` writes the result to `~/Downloads` and leaves the library alone. Tested 2026-10-05: book 51 (568 files) → 66 in 36 s, dry run. The write path was not re-run as a script; it is the same commands that were run by hand for book 120.

Calibre's plain EPUB → EPUB conversion does **not** help: it keeps the fragments.

## Limits and known trade-offs

- **qBittorrent's CSRF protection is switched off** (Options → Web UI). With it on, qBittorrent answers "Unauthorized" to any link that arrives from another page, such as the gateway page. Login is still required; the exposure is a malicious page acting through your logged-in browser session. The tiles use `rel="noreferrer"`.
- **Docker on the NAS is IPv4 only**, so only the IPv4 address is used in `WIREGUARD_ADDRESSES`.
- **Gluetun picks a different AirVPN server after every restart.** The forwarded port belongs to the account and stays valid.
- **Prowlarr is not behind the VPN** on purpose (many indexers block VPN addresses). Only two legal public indexers are configured (LinuxTracker, Internet Archive); add others in Prowlarr yourself.
- The homepage at `http://<nas>/` and its status page are separate from this repo; see `/volume1/docker/status-page/NOTES.md` on the NAS.

## More

- [`TODO.md`](TODO.md): the staged plan, what was verified at each step, and what is still open.
- [`CHANGELOG.md`](CHANGELOG.md): what changed and when.
