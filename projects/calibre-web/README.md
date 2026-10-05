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

## Sending books to a Kindle (email)

Calibre-Web's **Send to eReader** mails the book to the device's Send-to-Kindle address. Working on 2026-10-05; the settings:

| Setting | Value |
|---|---|
| Admin → Edit Email Server Settings | Server `mail.infomaniak.com`, port `465`, encryption **SSL/TLS**, login = the full mailbox address, "From" = the same address |
| Password | An Infomaniak **device password** named "Calibre-Web", not the mailbox password. Create it at manager.infomaniak.com → Mail → the address → Connected devices → Add → "Configure myself" (it asks you to confirm your login password first; the password is shown once). Stored encrypted in `app.db`. |
| User → Kindle E-mail | The device's own Send-to-Kindle address (amazon.com → Manage Your Content and Devices → Devices → the device). One device per user; several addresses can be comma-separated. |
| Amazon | The "From" address must be on **Approved Personal Document E-mail List** (Preferences → Personal Document Settings), or Amazon drops the mail silently. |

Gotchas:

- **Port 465 needs encryption set to SSL/TLS.** With another value Calibre-Web speaks plain SMTP to an SSL port, and the task fails after about a minute with "Smtplib Error sending e-mail: Connection unexpectedly closed".
- **Settings are cached in memory.** Editing `app.db` directly is not picked up until the container restarts (`sudo -n docker restart calibre-web`), and saving the web form before that writes the stale values back (it reset "From" to the placeholder). Prefer the UI; if you edit the database, restart before touching the form.
- **There is no Sent copy.** Check the chain in this order: Calibre-Web → Tasks ("Finished" means the mail left the NAS); Infomaniak → Mail → the address → Logs → Emails sent ("Received" means Amazon's server accepted it); Amazon → Content → Docs (the line "In 1 Device" means delivered) and View "Pending Deliveries" for deliveries that keep failing; then sync the Kindle.
- **Amazon can accept a file and never deliver it.** A badly split EPUB (thousands of tiny HTML files) stayed in Pending Deliveries for both devices while a small document delivered fine. See "Kindle EPUB check" in [gluetun-qbittorrent](../gluetun-qbittorrent/README.md#kindle-epub-check-warn-only-pre-process-hook); the cure is `fix-epub`. The 1.5 MB size Amazon shows is its converted copy, not the EPUB you sent.
- The converter path is empty (no `ebook-convert` in this container), so Calibre-Web sends the EPUB as it is; Amazon converts EPUB itself.
- **Kobo sync is enabled** (a shelf "Kobo Joost" has sync on) but nothing had synced as of 2026-10-04; the Kobo has not been pointed at this server.

## Permissions

`/volume1/books` is owned by `calibre` with an ACL. Only uid 1028 can write to the library, which is why LazyLibrarian also runs as 1028.
