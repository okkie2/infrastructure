# Redacted deployment reference

Captured from OK040 on 2026-10-20. These files document the active Volition deployment and recovery path. `compose.tunnel-client.yaml` and the recovery scripts are copied from `/volume1/homes/master/volition-deploy`. `tunnel-client.yaml.example` redacts the tunnel ID; `volition.env.example` contains placeholders. Secret values are not included.

This is a reference snapshot, not a ready-to-run deployment bundle. The tunnel config example needs the actual tunnel ID and the protected secret files on the NAS. The server deployment script needs the real notes directory and protected environment file. The files here do not change the NAS deployment.

## Active server settings

On 2026-10-20 the running server was `ghcr.io/okkie2/volition@sha256:ab0c5956db21b7758538959b53812a39627efe9d1a99f2fdaf22d4c7aa413a20`, user `1029:100`, read-only root filesystem, all capabilities dropped, `no-new-privileges`, 512 MB memory maximum, and a 32 MB no-exec, no-suid `/tmp`. It publishes `100.126.55.95:8766` and mounts `/volume1/homes/joost/Volition/notes` read-write at `/notes`. The server uses Docker's default bridge network. The live inspection reported no active PID limit, despite `deploy.sh` specifying `--pids-limit 128`; treat that as a deployment-script/runtime discrepancy.

The active `deploy.sh` accepts a digest-pinned image, notes directory, protected environment file, numeric user, mount mode, and publish address. It rejects mutable image references, preflights the image with a read-only mount, starts the replacement with the controls above, waits for health, runs the MCP smoke check, and retains the prior container for rollback. The live deploy observed on 2026-10-20 matches the documented image, mount, access, filesystem, capability, memory, and tmpfs settings; the missing PID limit is the noted exception. The previous-container rollback restores the image only; it does not undo note changes.

The active environment file contains `VOLITION_TOKEN`, `VOLITION_GIT_NAME`, and `VOLITION_GIT_EMAIL`. The token must be random ASCII, at least 32 characters, with no whitespace. On OK040, the deployment directory and secrets directory were mode `0700`; the environment file and both credential files were mode `0600`, owned by `master:users`.

## MCP authorization and operations

The running image's `/app/src/volition/http.py` wraps the HTTP app in bearer-token authorization. It requires exactly one matching `Authorization: Bearer …` header on every route except `/health`, uses constant-time comparison, and returns HTTP 401 for a missing or mismatched header. It also enables DNS-rebinding protection and restricts allowed hosts/origins to loopback and the configured publish host.

The running image's `/app/src/volition/server.py` registers two MCP tools:

- `query`: read-only catalogue, folder, document, and search operations.
- `capture`: create or edit Markdown documents. Edits can require an expected revision; a request ID makes retries idempotent. There is no delete, shell, or general filesystem MCP tool.

This behavior was read from the running image matching the server digest above. The application source itself is not copied into this repository.

The same bearer token authorizes both tools. There is no per-user identity or per-tool authorization layer; any client holding the token can query all notes and call `capture` to create or edit them.

## Tunnel client and network

The live Compose service is recorded in `compose.tunnel-client.yaml`. It runs as `1026:100` with a read-only root filesystem, all capabilities dropped, `no-new-privileges`, and a 16 MB no-exec, no-suid `/tmp`. It mounts only its config and two credentials read-only. It publishes no host port. Its local health endpoint listens on container loopback port 8080.

The tunnel client uses the `volition-tunnel-egress` bridge network (`172.24.0.0/24`) at `172.24.0.2`; the config forwards requests to Volition's Tailscale-bound address and supplies the bearer credential from a protected file. The observed tunnel image was `ghcr.io/openai/tunnel-client:latest`, resolving on 2026-10-20 to `ghcr.io/openai/tunnel-client@sha256:4605ea909701668d3bdcbe6152558e068e24006aa96ca5518ca67f786a1bce13`. Watchtower updates the `latest` target automatically every six hours.

**Egress control gap:** the tunnel Compose comments require a persistent egress policy, but the 2026-10-20 read-only firewall check found only `-A DOCKER-USER -j RETURN`. No container-specific egress allow-list was visible there. The effective firewall path still needs review and an approved persistent restriction. Until then, do not describe the tunnel network as egress-restricted.

## Recovery watcher

`volition-recover.service` starts `volition-recover-watch.sh` after Container Manager. The watcher follows Docker start events for the Tailscale container, waits for `100.126.55.95` to appear, then calls `recover-tailscale-bind.sh`. That helper restarts Volition only for the documented bind-address startup failure and confirms the container becomes healthy before running the MCP smoke check. `install-recovery.sh` installs the watcher and helper root-owned under `/usr/local/libexec/volition` with mode `0755`, installs the systemd unit with mode `0644`, and enables the service.

The actual recovery files are included here for review. The deployment scripts are not run as part of this documentation change.

## Update and restore

The Volition server's deployment script requires an immutable `IMAGE@sha256:…` reference; Watchtower does not update it. Retrieve and review the intended release digest, then use the deployment script on the NAS. The tunnel client currently uses `latest` and is auto-updated by Watchtower; its observed digest above is a snapshot, not a pin. Decide on and apply a digest-pinned update policy before treating the tunnel update path as controlled.

Restore `/volume1/homes/master/volition-deploy` from the `Timemachine Homes` backup. Restore the protected environment and credential files from the password manager or their separately protected backup; never substitute the example files as credentials. Restore notes from the daily `Volition Daily Copy` snapshot or `Timemachine Homes` backup before starting Volition.
