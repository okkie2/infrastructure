# calibre-web

Web reader and library front end for the Calibre library at `/volume1/books/Library`. LazyLibrarian (in [gluetun-qbittorrent](../gluetun-qbittorrent/)) imports new books into the same library.

| Item | Value |
|---|---|
| Container | `calibre-web`, project `calibre-web` in `/volume1/docker/calibre-web` (a registered Container Manager project, so Action → Build works) |
| Image | `lscr.io/linuxserver/calibre-web:nightly`, auto-updated by Watchtower |
| Compose file | [`docker-compose.yml`](docker-compose.yml) |
| Port | `8083` |
| Runs as | uid 1028 (`calibre`), gid 100 |
| Config | `/volume1/docker/calibre-web/config` (app database, users, settings) |
| Library | `/volume1/books` mounted at `/books`; set the library path in the UI to `/books/Library` |
| Startup hook | [`custom-cont-init.d/00-kepubify-symlink.sh`](custom-cont-init.d/00-kepubify-symlink.sh), mounted at `/custom-cont-init.d` |

## Drift to fix

The NAS compose file says `:latest`, but the running container is `:nightly`. This repo records `:nightly`. Update the NAS file to match, or choose deliberately.

## The kepubify hook

Calibre-Web only recognises a binary named `kepubify-linux-64bit`, but the image ships `kepubify`. A symlink does not work because Calibre-Web resolves the real path before checking the name (upstream issue janeczku/calibre-web#3679), so the hook copies the file under the expected name on every start and writes a diagnostics file `kepubify-init-debug.log` into `/config`. Without the hook Calibre-Web does not detect kepubify. In the UI, point the kepubify path at `/usr/bin/kepubify-linux-64bit`.

## Rebuild

```sh
ssh ok040 'mkdir -p /volume1/docker/calibre-web/config /volume1/docker/calibre-web/custom-cont-init.d'
ssh ok040 'cat > /volume1/docker/calibre-web/docker-compose.yml' < projects/calibre-web/docker-compose.yml
ssh ok040 'cat > /volume1/docker/calibre-web/custom-cont-init.d/00-kepubify-symlink.sh' < projects/calibre-web/custom-cont-init.d/00-kepubify-symlink.sh
ssh ok040 'chmod +x /volume1/docker/calibre-web/custom-cont-init.d/00-kepubify-symlink.sh'
```

Then create the project in Container Manager (path `/docker/calibre-web`, existing compose file). On first start the default login is `admin` / `admin123`; change it immediately, set the library to `/books/Library`, and recreate any other users. With a restored `config` folder none of this is needed.

## Permissions

`/volume1/books` is owned by `calibre` with an ACL. Only uid 1028 can write to the library, which is why LazyLibrarian also runs as 1028.
