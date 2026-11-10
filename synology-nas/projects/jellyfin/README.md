# jellyfin

Jellyfin media server on the Synology DS225+, alongside the existing Plex install. Read-only access to Plex's Movies/TV libraries, plus a Jellyfin-only Music library and a new Audiobooks library.

It is written for one household NAS, not as a reusable product. The repo holds the Compose project and the working notes; the container, its config, and the media live on the NAS.

## Why

- **Doesn't touch Plex.** `/media/movies`, `/media/tv`, and `/media/music` are bind-mounted `:ro` specifically so Jellyfin's library scanner can never modify or delete anything in Plex's libraries, no matter what it thinks it's doing. This mattered in practice: a scan once tried to remove a real album after a false-positive "missing file" detection — the removal failed only because of this read-only mount, not because of any safeguard in Jellyfin itself.
- **Scope kept deliberately narrow.** Only Music and Audiobooks are active Jellyfin libraries, on purpose — Movies/TV stay Plex's job. `/media/movies` and `/media/tv` are mounted into the container (available if that changes later) but no Jellyfin library was ever created for them.
- **QuickSync passthrough** via `/dev/dri` and the `videodriver` group for hardware transcoding.

## Setup

Assumes SSH access to the NAS as `ok040` and a running Container Manager.

1. **Create directories and deploy the Compose file:**

   ```sh
   ssh ok040 'mkdir -p /volume1/docker/jellyfin/config /volume1/docker/jellyfin/cache'
   ssh ok040 'cat > /volume1/docker/jellyfin/docker-compose.yml' < projects/jellyfin/docker-compose.yml
   ```

2. **Create the project** in DSM: Container Manager → Project → Create. Name `jellyfin`, path `/docker/jellyfin`, "Use existing docker-compose.yml", start it.

3. **First login** at `http://<nas>:8096`, create the admin account, then add the Music library pointing at `/media/music`.

## Libraries

| Library | Content type | Path | Notes |
|---|---|---|---|
| Music | Music | `/media/music` | ~5,600 tracks across 327 albums. See [Genre taxonomy](#genre-taxonomy) below. |
| Audiobooks | Books | `/media/audiobooks` | Content type is "Books", not "Music" — this is the Jellyfin-recommended choice for audiobooks specifically because it tracks and resumes playback position per item; Music-type libraries don't reliably do this. Trade-off: no online metadata fetch for Books, so covers rely on embedded art or a manually dropped `cover.jpg`. |

Movies and TV Shows are mounted (`/media/movies`, `/media/tv`) but intentionally have no library configured — Plex remains the player for those.

## Genre taxonomy

The Music library's genre tags were a mess of legacy/inconsistent values. They were replaced with a single deliberate taxonomy (13 genres: Classical, Jazz, Pop/Rock, Dance/Club, Lounge/Chillout, Latin/World, Folk, Nederpop, Reggae, Soundtrack, Children's, Chanson, Christmas), assigned per artist/album folder and written as the `Genre` ID3 tag on every file.

**Known trap — do not re-run "Replace all metadata" with internet providers enabled.** Jellyfin's Music library has `MusicBrainz`/`TheAudioDB` as available metadata downloaders. Running a full metadata replace with those enabled re-fetches each artist/album's *own* genre/style tags from those services (things like "art pop", "baroque pop", "70-ties", "contemporary r&b") and layers them on top of the curated taxonomy rather than replacing it — this happened once already and had to be cleaned up. The Music Albums metadata downloaders are now unchecked in the library settings (Dashboard → Libraries → Music → Manage library → Metadata downloaders (Music Albums)), but note that unchecking them does **not** retroactively stop an already-queued refresh — a large backlog of queued MusicBrainz artist lookups from the earlier incident kept running in the background for a while after, causing an unrelated general slowdown (see Known issues).

To reapply or extend the taxonomy: genre tags were set two ways during this work, and either still works —

- **File-level (ID3 tags):** walk the library and set the `Genre` tag directly on the audio files with `mutagen`, then let Jellyfin's real-time monitor or a library scan pick up the change.
- **API-level (bypasses Jellyfin's fetchers entirely, more reliable):** `GET /Users/{userId}/Items/{itemId}` for the full item DTO, set `Genres` and `GenreItems`, `POST /Items/{itemId}` with the modified DTO. This is what actually fixed the pollution — disabling the metadata-downloader checkboxes alone did not stop already-mismatched genre associations from showing, but overwriting the item's `Genres` field directly via the API did. A Jellyfin API key is needed (Dashboard → API Keys); auth header is `Authorization: MediaBrowser Token="<key>"`.

## Collections

Three Collections group albums that are scattered across different artist folders:

| Collection | Albums | Spans folders |
|---|---|---|
| Buddha-Bar | 15 | Buddha-Bar, Buddha-Bar (CD Series), Ravin, VA, Various, David Visan, Suat Atesdagli, Compilations |
| Quentin Tarantino Soundtracks | 3 (Kill Bill, Kill Bill Volume 2, Pulp Fiction) | Quentin Tarantino |
| Rizzy | 15 monthly mixes (Dec 2024–July 2026) | Rizzy |

Created via `POST /Collections` (empty, no `Ids`) then `POST /Collections/{id}/Items` to add items separately — creating a collection with items in one call makes Jellyfin generate collage artwork synchronously, which hangs for anything more than a handful of albums.

**Known issue, unresolved:** these three collections don't appear in the Music library's "Collections" tab browse view, despite being fully correct (right `ParentId`/`TopParentId`, right child items — verified directly against a collection created through the UI, which is visible). They work perfectly when opened by direct link. The cause wasn't found — ruled out: filters, browser cache, `ParentId`, `TopParentId`, item metadata refresh, and server load/task backlog. Something about the per-user, library-scoped `BoxSet` query excludes them that a UI-driven creation doesn't trigger. Next step if this gets revisited: compare Jellyfin's actual SQL query (server debug logging) between a working and a non-working collection, or try recreating one via 15 manual UI clicks to see if the UI-driven path genuinely differs.

## Known issues

- **Collections tab visibility** — see above.
- **Two genres display in lowercase** if they happen to collide with a genre name MusicBrainz had already created during the pollution incident (case-insensitive dedup keeps whichever casing was created first). `Nederpop`, `Pop/Rock`, and `Reggae` were manually fixed by renaming the `MusicGenre` item entity directly (`POST /Items/{genreEntityId}` with a corrected `Name`). Fourteen now-orphaned genre entities (0 real items, e.g. `Disco`, `Blues`, `Classic Rock`) are still sitting in Jellyfin's genre index but don't appear in any browse view — left alone since deleting them risked side effects on items whose join-table rows hadn't fully cleared.
- **No Sonos integration exists.** Jellyfin has no official SMAPI bridge. Community options if this is ever wanted: [JellyfinSonos](https://github.com/jakepi84/JellyfinSonos) (self-hosted) or [Sonofin](https://github.com/munkinasack/Sonofin) (Cloudflare Worker) — both limited to the default music library, weak playlist support, no favorites sync.

## Configuration

| What | Where |
|---|---|
| Stack definition | `docker-compose.yml` (project `jellyfin`) |
| Config/state | `/volume1/docker/jellyfin/config` on the NAS |
| Cache/transcodes | `/volume1/docker/jellyfin/cache` on the NAS |
| Web UI | `http://<nas>:8096`; from outside the house use the NAS's Tailscale address |
