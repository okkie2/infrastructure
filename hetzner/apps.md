---
title: "Add an app to the Hetzner platform"
created: "2026-11-14"
created_by: "Claude Code (Opus 5.5), at the owner's request"
creation_reason: "The Hetzner host and platform were provisioned without an app; the owner needs a repeatable recipe to install apps and their databases."
purpose: "Step-by-step procedure for onboarding one containerised app, with its own PostgreSQL database, onto ubuntu-4gb-hel1-1."
provenance:
  type: original
  description: "Written from the Ansible platform role and the smoke tests run on 14 November 2026 against the live server."
  sources:
    - reference: "ansible/roles/platform/"
      description: "Templates and tasks the procedure drives."
    - reference: "ubuntu-4gb-hel1-1/operations.md"
      description: "Verified host state and access path."
ai:
  involvement: drafting
  description: "Claude drafted the procedure; the owner chose the platform design decisions it implements. Codex updated its backup status on 15 November 2026."
updated: "2026-11-15"
updated_by: "Claude Code (Fable 5.2)"
update_reason: "Noted that public web is open since the first app, the host-built private image option, and Caddy's request time limits."
---

# Add an app to the Hetzner platform

The platform on `ubuntu-4gb-hel1-1` is one Caddy reverse proxy and one shared PostgreSQL 18 server, run by Docker Compose from `/srv/platform` and managed by [Ansible](ansible/). Each app is its own Compose project under `/srv/apps/<app>/`.

## What the platform gives each app

Declaring an app in `ansible/group_vars/all.yml` → `platform_apps` creates:

| Item | Value |
| --- | --- |
| Edge network | `<app>_edge`, shared only by Caddy and this app |
| Database network | `<app>_db`, `internal: true`, shared only by PostgreSQL and this app |
| Database and role | Both named `<app>`; the role owns the database and is `NOSUPERUSER NOCREATEDB NOCREATEROLE`. `PUBLIC` has no access, so other app roles cannot connect. |
| Database password | Generated on the host at `/srv/apps/<app>/secrets/db_password`, owned by the app's `uid` with mode 0400. It never passes through Git, Ansible output or a process list. |
| HTTPS route | `<domain>` → `<upstream>`, with an automatic certificate once DNS and the firewall are open |

Apps on different edge or database networks cannot reach each other, and PostgreSQL shares no network with Caddy. PostgreSQL publishes no port. Connections from containers always need a password (scram-sha-256), and the `postgres` superuser is rejected over any network. App roles cannot connect to other databases, including `postgres`.

Ansible refuses invalid entries:
- names that don't match `[a-z][a-z0-9_]*`;
- reserved names (`postgres`, `template0`, `template1`, `public`, `platform`, `caddy`, `pg_*`);
- duplicates;
- an `upstream` alias that doesn't start with the app's name, using `-` for `_`, so one app cannot capture another's traffic.

## Procedure

1. **Name and domain.** Pick a lowercase app name, matching `[a-z][a-z0-9_]*`; it becomes the database and role name. Point the domain's `A` record to `37.27.251.21` and its `AAAA` record to `2a01:4f9:c015:84a6::1`.

2. **Open public web traffic**, once only, for the first app (done on 15 November 2026 for Kibble; skip this step from now on), before declaring it so Caddy's certificate request can succeed. In `hetzner/opentofu`, run `tofu plan -var public_web_enabled=true`, review that only firewall rules change, then apply. Make the variable's default `true` in `variables.tf` so later plans keep it. This needs a read-write `HCLOUD_TOKEN`; see [operations](ubuntu-4gb-hel1-1/operations.md#runbook).

3. **Declare the app** in `ansible/group_vars/all.yml`:

   ```yaml
   caddy_acme_email: you@example.org   # once, before the first public domain
   platform_apps:
     - name: sinterapp
       domain: sinterapp.example.org
       upstream: sinterapp-web:8000    # network alias and port the app exposes on sinterapp_edge
       uid: 1000                       # uid the app container runs as; owns the password file
   ```

4. **Apply the platform.** Adding or removing an app recreates the Caddy and PostgreSQL containers, so every app is briefly offline. Do it at a quiet moment.

   ```sh
   cd hetzner/ansible && ansible-playbook site.yml --tags platform
   ```

5. **Install the app's Compose project** at `/srv/apps/<app>/compose.yaml`, with its non-secret config in `/srv/apps/<app>/.env` (root, 0600). The Compose file lives in the app repository; this is the shape the platform expects:

   ```yaml
   name: sinterapp
   services:
     web:
       image: codefloe.example/okkie2/sinterapp@sha256:<digest>   # pin by digest
       restart: unless-stopped
       user: "1000:1000"            # must match uid in platform_apps
       read_only: true              # add tmpfs or volumes for paths the app writes
       tmpfs: [/tmp]
       cap_drop: [ALL]
       security_opt: ["no-new-privileges:true"]
       env_file: .env
       environment:
         DB_HOST: postgres
         DB_NAME: sinterapp
         DB_USER: sinterapp
         DB_PASSWORD_FILE: /run/secrets/db_password
       secrets: [db_password]
       networks:
         edge: { aliases: [sinterapp-web] }
         db: {}
       mem_limit: 512m
       # No `ports:`. Caddy is the only container that publishes ports.
   secrets:
     db_password:
       file: ./secrets/db_password
   networks:
     edge: { external: true, name: sinterapp_edge }
     db:   { external: true, name: sinterapp_db }
   ```

   A private image can be built on the host instead of pulled: `git archive HEAD | ssh <host> 'sudo docker build -t <app>:<commit> -'`, then pin its local digest (`<app>@sha256:…` from `docker image inspect … --format '{{json .RepoDigests}}'`) and set `pull_policy: never`. Kibble does this.

   Caddy limits how long a client may take to send a request (headers 10 s, body 30 s; see `roles/platform/templates/Caddyfile.j2`). Raise `read_body` before an app accepts large uploads.

   If the app cannot read a `*_FILE` variable, build the connection URL in its entrypoint from the secret file. Do not paste the password into `.env`.

6. **Start and check it:**

   ```sh
   ssh joost@ubuntu-4gb-hel1-1.tail4d7938.ts.net
   sudo docker compose --project-directory /srv/apps/sinterapp up -d --wait   # /srv/apps is root-only; don't cd
   curl -sSI https://sinterapp.example.org
   ```

7. **Save the database password** in Proton Pass: `sudo cat /srv/apps/<app>/secrets/db_password`.

**Rotate a password:** write a new value into the file (`openssl rand -hex 32`, keeping its owner and mode), rerun step 4, then restart the app. Ansible updates the role but reports `ok`, not `changed`, and the running app keeps the old password until it restarts.

This exact shape (non-root, read-only, no capabilities, database through the secret file, HTTPS through Caddy) was tested end to end on 14 November 2026 with a throwaway app, then removed.

## Remove an app

Stop its Compose project, remove it from `platform_apps`, and rerun step 4. The database, role, secret file and the two `<app>_*` Docker networks are deliberately kept. After a final backup, remove them by hand: `DROP DATABASE`/`DROP ROLE` via `docker compose exec postgres psql -U postgres`, `docker network rm <app>_edge <app>_db`, and `rm -r /srv/apps/<app>`.

## Backups

Nightly PostgreSQL dumps are pulled to OK040, and an isolated restore trial succeeded on 15 November 2026. See the [backup design and restore record](../synology-nas/projects/hetzner-backup/README.md) and [operations evidence](ubuntu-4gb-hel1-1/operations.md#isolated-restore-trial-15-november-2026). Caddy certificates are not backed up.
