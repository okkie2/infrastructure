# keeper

Keeper stores plain Markdown notes in subject folders and is the backing store for the notes in `/volume1/homes/joost/Notes`. Image `ghcr.io/okkie2/keeper` (source: https://github.com/okkie2/volition).

| Item | Value |
|---|---|
| Container | `keeper`, project `keeper-managed` in `/volume1/docker/keeper-managed` (owned by `joost`, mode 750) |
| Image | `ghcr.io/okkie2/keeper@sha256:2f4715e3…c245433`, pinned by digest; the full digest is in the compose file |
| Compose file | [`docker-compose.yml`](docker-compose.yml) |
| Secret | `KEEPER_TOKEN` in `/volume1/docker/keeper-managed/.env` (see [`.env.example`](.env.example)). Compose refuses to start without it. |
| Port | `100.126.55.95:8766`, bound to the NAS Tailscale address only. |
| Data | `/volume1/homes/joost/Notes` mounted read-write at `/notes` |
| Runs as | `1029:100` (user `joost`), read-only root filesystem, all capabilities dropped, `no-new-privileges`, 512 MB memory limit, `HOME=/tmp` |

## Rebuild

```sh
ssh ok040 'mkdir -p /volume1/docker/keeper-managed'
ssh ok040 'cat > /volume1/docker/keeper-managed/docker-compose.yml' < projects/keeper/docker-compose.yml
# create .env with KEEPER_TOKEN=<token>, owner joost, chmod 600
ssh ok040 'cd /volume1/docker/keeper-managed && sudo docker compose up -d'
```

The image is public on GHCR, so no login is needed to pull it. Because it is digest-pinned, Watchtower does not manage it; move the digest by hand when upgrading.

## Backup

The Notes folder is copied daily at 02:00 by the "Notes Daily Copy" task (newest 8 copies kept in `Notes-backups`). See [host](../host/). The Keeper container itself holds no state.

## Notes

- The binding to the Tailscale IP means Keeper stops being reachable if the gateway's IP changes ([tailscale-gateway](../tailscale-gateway/)).
- `KEEPER_PUBLISH_HOST` is the same Tailscale IP, and the git identity Keeper commits with is set in the compose file.
