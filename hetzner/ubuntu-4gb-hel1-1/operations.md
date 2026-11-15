---
title: "Operations: ubuntu-4gb-hel1-1"
created: unknown
created_by: unknown
creation_reason: "Record the Hetzner server's verified state and the path to reproducible management."
purpose: "Current operations record for ubuntu-4gb-hel1-1: sources of truth, verified state, runbook, and recovery."
provenance:
  type: mixed
  description: "Verified-state tables are first-hand observations from read-only CLI, SSH and console checks on 10, 14 and 15 November 2026. The management split and procedures are interpretation based on the cited vendor documentation."
  sources:
    - reference: "../ansible/"
      description: "Host configuration as code."
    - reference: "../opentofu/"
      description: "Hetzner resources as code."
    - reference: "../../synology-nas/projects/hetzner-backup/README.md"
      description: "Backup installation, pull behavior, retention, and isolated restore trial."
    - reference: "https://docs.hetzner.com/cloud/firewalls/faq/"
      description: "Cloud Firewall behaviour."
    - reference: "https://docs.docker.com/engine/network/packet-filtering-firewalls/"
      description: "Docker bypassing host firewalls."
ai:
  involvement: drafting
  description: "Earlier versions' authorship is not recorded. Codex updated the verified state on 15 November 2026 from read-only SSH inspection and recorded backup and restore evidence."
updated: "2026-11-15"
updated_by: "Claude Code (Fable 5.2)"
update_reason: "Recorded the first app (Kibble) going live: public web ports opened, Caddy route and time limits, deployment checks, and backup coverage."
---

# Operations: ubuntu-4gb-hel1-1

This is the server's operations record. It separates verified state from plans and never stores secret values.

## Layout and sources of truth

| Component | Location | Source of truth | Recovery |
| --- | --- | --- | --- |
| Hetzner resources | Project `default`: server, two primary IPs, firewall `prod-ingress` | [`hetzner/opentofu`](../opentofu/); state is local on the Mac and not in Git | `tofu plan`/`apply`. If state is lost, re-import with [`imports.tf`](../opentofu/imports.tf). |
| Host configuration | Ubuntu 26.04.1 | [`hetzner/ansible`](../ansible/) | `ansible-playbook site.yml` |
| Platform runtime | `/srv/platform`: Caddy and PostgreSQL via Docker Compose | `ansible/roles/platform` templates | Rerun the `platform` tag |
| Apps | `/srv/apps/<app>` | Each app's repository, plus `platform_apps` in Ansible | [Add an app](../apps.md) |
| Secrets | Proton Pass; generated host secrets under `/srv/**/secrets/` (root or postgres-owned, 0400 or 0600) | Proton Pass | Recover the vault, then reprovision |
| Data | Docker volume `platform_postgres_data`; Caddy certificates in `platform_caddy_data` | PostgreSQL dumps are pulled nightly to OK040; Caddy certificates are not backed up | [Hetzner backup pull](../../synology-nas/projects/hetzner-backup/README.md) |
| Logs | journald; Docker `local` log driver, 3 × 10 MB per container | OS and Docker configuration | Rebuildable |

## Verified state: 15 November 2026

Verified by commands run from the Mac during and after provisioning, including read-only SSH inspection on 15 November 2026.

| Item | Verified state |
| --- | --- |
| Hetzner resource | ID `175269905`, CX23, `hel1`, 2 vCPU, 4 GB RAM, 40 GB disk. Labels `environment=prod` and `managed_by=opentofu`. **Delete and rebuild protection on.** |
| Public addresses | IPv4 `37.27.251.21` (primary IP `161396837`) and IPv6 `2a01:4f9:c015:84a6::/64` (`161396838`). Both have `auto_delete=false` and delete protection, so they outlive the server. |
| OpenTofu | All three resources imported. The firewall and its attachment were created by OpenTofu. A follow-up `tofu plan` reports no changes. |
| Cloud Firewall | `prod-ingress` (ID `12055976`) is attached and `applied`. Inbound allows ICMP, UDP 41641 (Tailscale direct) and, since 15 November 2026, TCP 80, TCP 443 and UDP 443 for Caddy (`public_web_enabled` now defaults to `true`). No SSH, no outbound rules. Public TCP 22 is still closed on IPv4, checked after the change; a follow-up `tofu plan` reports no changes. |
| Admin access | User `joost`, key-only (password locked), passwordless sudo, not in the `docker` group. Reached over Tailscale only: `ssh joost@ubuntu-4gb-hel1-1.tail4d7938.ts.net`. |
| SSH policy | `/etc/ssh/sshd_config.d/00-hardening.conf`; cloud-init's `50-cloud-init.conf` was removed. `sshd -T` on 15 November shows `usepam yes`, `permitrootlogin no`, `passwordauthentication no`, `kbdinteractiveauthentication no`, `authenticationmethods publickey`, and `allowusers joost` plus `nasbackup@100.126.55.95`. Root-by-key and unknown users are refused. |
| SSH host key | ED25519 `SHA256:DeixvRwYazTkhYE0lg3k30m9f8C3efUKmbBDcwYwvTc`, unchanged and seen identically over the tailnet |
| Tailscale | Read-only `tailscale status --json` over SSH on 15 November showed backend `Running`, node `Online`, hostname `ubuntu-4gb-hel1-1`, IP `100.105.28.57`, and tag `tag:hetzner-prod`. Routes, DNS and Tailscale SSH are not accepted. The join used a single-use key (`tag:hetzner-prod`), which the Tailscale console showed as invalidated on 14 November 2026, with no valid auth keys left. |
| Tailnet policy | Grant: `joost.okkinga@gmail.com` → `tag:hetzner-prod` on tcp 22 and 443. No rule lets the tag initiate connections. From the server, the Mac, `ok040-gateway` (22, 445) and `kb-bnjx` (22) all time out. |
| Root password | Kept as break-glass for the Hetzner web console. The owner confirmed the console login works on 14 November 2026. |
| Updates | `unattended-upgrades` enabled (security pocket by default) |
| Docker | Docker CE 29.9.3, Compose v5.7.1; `daemon.json` sets the `local` log driver (10m × 3) and `live-restore` |
| Platform | Compose project `platform`: `caddy:2.11.9` publishes 80/443 (TCP and UDP), open to the internet since 15 November 2026, with request time limits (headers 10 s, body 30 s, idle 2 min); `postgres:18.7` is healthy with no published port. They share no network: Caddy is on `platform_default`, PostgreSQL on internal networks only. Config directories, not single files, are mounted so updates take effect. Memory limits: Caddy 256 MB, PostgreSQL 1 GB. |
| PostgreSQL auth | Managed `pg_hba.conf`. Inside the container, local and loopback connections are `trust`, which needs root on the host. The `postgres` superuser is rejected from any network, verified. Other network connections use `scram-sha-256`; a wrong password is refused. `PUBLIC` has no access to app databases or `postgres`. |
| Per-app path | Tested end to end with a throwaway app `smoke`, then removed:<br>- declared through `platform_apps`; check mode was clean and a second apply showed `changed=0`;<br>- a non-root, read-only container read its 0400 password file and wrote to its database;<br>- its web network cannot resolve PostgreSQL, and its role cannot open `postgres`;<br>- Caddy served it over HTTPS on the tailnet;<br>- a reserved name (`postgres`) was refused. |
| Ansible | `--check --diff` runs cleanly. Full `site.yml` over the tailnet path, twice after the final change: `changed=0` both times. |
| Apps | **kibble** (first app, 15 November 2026): `https://wordkibble.com`, Compose project `/srv/apps/kibble`, image `kibble@sha256:13e8bf1749a4aad4c7c019c7d6899d7ebc0d8208418d36fdd75c1b5e0cb297d6` built on the host (private, `pull_policy: never`), uid 1000, read-only, 256 MB. Database and role `kibble` (not superuser). The waiting-list form is closed, so the database holds no personal data. Details: `~/Code/kibble/docs/operations.md`. |
| First-app checks, 15 November 2026 | HTTPS answers on IPv4 and IPv6; certificate from Let's Encrypt for `wordkibble.com`, valid to 13 February 2027; HTTP redirects to HTTPS; `/health` returns `ok`; after `docker restart platform-postgres-1` the app answered again without a restart; a second Ansible run reported `changed=0`. `www.wordkibble.com` has DNS but no route yet. IPv6 visitors reach Caddy through Docker's proxy, so Caddy sees the gateway address `172.20.0.1` for them, not their own address. |
| Capacity after deploy | About 3.0 GB of RAM available with Kibble running (Kibble 50 MB, PostgreSQL 33 MB, Caddy 18 MB); disk 3.7 of 38 GB used |
| Backups | Nightly PostgreSQL dump and NAS pull installed; OK040 reported success at 10:12 local on 15 November 2026, fetched one copy, and identified stamp `2026-11-15T091239Z` as newest. The stamp contains `db-backup_trial.dump` and `globals.sql`; transfer checksum verification succeeded. The NAS copy remains in its retention set. Caddy data is not backed up. A dump started by hand after the Kibble deployment (stamp `2026-11-15T152918Z`) contains `db-kibble.dump`; the NAS pull of it has not been observed yet. |

### Isolated restore trial: 15 November 2026

Restored `db-backup_trial.dump` from NAS stamp `2026-11-15T091239Z` into a throwaway `postgres:18.7` container with `network=none`. Production and restored databases each contained 1,000 deterministic rows; both produced SHA-256 `182ecb1e65491145dc95a975f95ae6621679ed4a3a1354c05a76710475ac77db`. Afterward the database and role counts were zero, the container was absent, and `/home/joost/restore` was absent. The trial-created backup copy remains in the NAS retention set.

The 10 November 2026 baseline was: root password SSH open to the internet, no firewall, no Docker. The journal back to creation (9 November) showed tens of thousands of failed password attempts and no successful login from any address other than the owner's.

## Runbook

**Host configuration**, from `hetzner/ansible`:

```sh
ansible-playbook site.yml --check --diff     # preview
ansible-playbook site.yml                    # apply; expect changed=0 when nothing drifted
ansible-playbook site.yml --tags platform    # platform and app declarations only
```

**Hetzner resources**, from `hetzner/opentofu`. The stored `hcloud` context is read-only. For an apply, create a short-lived read-write token in the Hetzner console, keep it in Proton Pass, export it as `HCLOUD_TOKEN`, and revoke it afterwards.

```sh
tofu plan -out=plan.tfplan     # check: 0 to destroy, no "must be replaced"
tofu apply plan.tfplan
rm plan.tfplan
```

**Rebuild from scratch: outline only, not yet rehearsed.** This is a TODO item. The code does not yet support it unattended. Known requirements:
1. **OpenTofu:** remove delete and rebuild protection and `prevent_destroy` deliberately. Add `public_net` pointing at the protected primary IPs so the new server keeps its addresses. Add an `ssh_keys` entry (or cloud-init) so root can log in for the bootstrap. If state was lost, also import firewall `12055976`.
2. **Remove the old node** from the tailnet so the new one gets the name `ubuntu-4gb-hel1-1`.
3. **Bootstrap SSH path:** add a firewall rule allowing SSH from your current IP only (rather than detaching the firewall), and remove the old host key from `~/.ssh/known_hosts`.
4. **Bootstrap run:** `TS_AUTHKEY=<new tagged single-use key> ansible-playbook site.yml -e ansible_host=<public IP> -e ansible_user=root -e ssh_hardening_enabled=false`
5. **Verify** `ssh joost@ubuntu-4gb-hel1-1.tail4d7938.ts.net` and `sudo -v`. Then run the playbook normally, remove the temporary SSH rule, and restore data.

**Lockout recovery:** use the Hetzner web console with the root password. If that fails, use Rescue; see [rescue.md](rescue.md). Root SSH is disabled, but local console login is not.

## Security notes

- Docker-published ports bypass any host firewall. The Hetzner Cloud Firewall is the public boundary, and only Caddy may publish ports.
- The Cloud Firewall does not filter tailnet traffic. Tailnet exposure is governed by the tailnet policy above.
- Passwordless sudo means the admin SSH key is the only barrier to root. Moving to password sudo is a tracked follow-up.

## Outstanding work

Track remaining work in the [Hetzner TODO](../TODO.md).

## References

- [Hetzner Cloud Firewall behaviour](https://docs.hetzner.com/cloud/firewalls/faq/)
- [Hetzner Cloud provider: server resource](https://registry.terraform.io/providers/hetznercloud/hcloud/latest/docs/resources/server)
- [OpenTofu sensitive state](https://opentofu.org/docs/language/state/sensitive-data/)
- [Docker and host firewall behaviour](https://docs.docker.com/engine/network/packet-filtering-firewalls/)
- [Tailscale tags](https://tailscale.com/kb/1068/tags)
