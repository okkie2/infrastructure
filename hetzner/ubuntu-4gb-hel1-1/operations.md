# Operations: ubuntu-4gb-hel1-1

This is the server's current operations record and the proposed path to reproducible management. It separates verified state from future plans. Secret values are never stored here.

## Layout and sources of truth

| Component | Location/input | Source of truth | Recovery |
| --- | --- | --- | --- |
| Hetzner infrastructure | Hetzner Cloud project `default`; server `ubuntu-4gb-hel1-1` | Hetzner account and, when adopted, OpenTofu state/configuration | Import and reconcile existing resources, or recreate from reviewed OpenTofu config |
| Server configuration | Ubuntu 26.04.1 on the VPS | Proposed Ansible inventory and playbooks; currently partly manual | Reapply reviewed playbooks over verified SSH |
| Bootstrap | Hetzner `user_data` / cloud-init on a future create or rebuild | Versioned cloud-init template, with no secrets | Create a limited admin and install its public key, then hand off to Ansible |
| Application runtime | Docker Engine and Compose on the VPS | Not installed yet; planned application repositories and Compose files | Install from supported instructions, then deploy the pinned image and Compose project |
| Application configuration | Per-app runtime configuration, outside source repositories | Deployment configuration; schema/examples in app repositories | Recreate from documented variable names and password-manager items |
| Secrets | Password manager; exact items/values are not recorded here | Proton Pass is the user's preferred source of truth | Recover vault access, then provision only required values to the server |
| Application data | No production containers or data are present yet | Future persistent host paths / Docker volumes | Consistent database and volume backup, followed by a restore test |
| Logs and caches | Ubuntu system logs; no Docker logs yet | OS/runtime configuration | Recreate caches; retain bounded operational logs as needed |

The workspace root `Infrastruture/` is not currently a Git repository. The `synology-nas/` subfolder is a separate repository. Before adding OpenTofu state, Ansible inventory or playbooks, create a dedicated Git repository for `hetzner/`. The initial state-storage proposal is local state on the Mac, provided FileVault is enabled and state backups are encrypted; exclude state, plans, `.terraform/`, credentials and secrets from Git. Revisit a remote locked backend before running OpenTofu from multiple machines or automation. Do not commit private keys, passwords, API tokens, runtime secrets or OpenTofu state files.

## Verified live state — 10 November 2026

Checked through Hetzner's read-only CLI, SSH and the Ubuntu console:

This is still a bare Ubuntu server: no applications, Docker containers or production data have been deployed. Current access consists of the Ubuntu root password, the Mac's installed SSH public key, and the local Hetzner CLI context.

| Item | Verified state |
| --- | --- |
| Hetzner resource | Server ID `175269905`, name `ubuntu-4gb-hel1-1`, type CX23, Helsinki (`hel1`), 2 shared vCPU, 4 GB RAM, 40 GB disk |
| Operating system | Ubuntu 26.04.1 LTS, x86_64 |
| Public network | IPv4 `37.27.251.21`; IPv6 prefix `2a01:4f9:c015:84a6::/64` |
| Rescue recovery | Root password was set inside the mounted Ubuntu system using Hetzner's documented Rescue/chroot procedure; Ubuntu root login then succeeded. See [rescue.md](rescue.md). |
| Ubuntu root password | Changed again with `passwd` from the Ubuntu root shell. Its value is intentionally absent here. Save and manage it in Proton Pass; confirm the current item there. |
| SSH host identity | ED25519 fingerprint verified against both the Ubuntu console output and SSH's presented key: `SHA256:DeixvRwYazTkhYE0lg3k30m9f8C3efUKmbBDcwYwvTc`. Reverify after a rebuild or host-key rotation. |
| SSH access | Mac public key `~/.ssh/id_ed25519.pub` was installed for `root` with `ssh-copy-id`; a fresh key-based SSH command returned `root`. The private key stays on the Mac. |
| SSH authentication policy | `sshd -T` reports `permitrootlogin yes`, `pubkeyauthentication yes`, and `passwordauthentication yes`. Root password SSH remains enabled; key installation did not disable it. |
| Hetzner Cloud Firewall | None attached; `hcloud firewall list` returned no firewalls. |
| Ubuntu UFW | Inactive (`ufw status verbose`). |
| Listening public services | SSH on TCP 22 for IPv4 and IPv6. No web or database listener was present. |
| Docker / Compose | Docker command absent; service inactive. Docker and Compose are not installed. |
| Hetzner backups | Disabled. |

No firewall, backup setting, package installation, non-root account, or application deployment was changed during these checks. The root password and `ssh-copy-id` key installation were changed by the owner as recorded above.

## Work completed

1. Created the Hetzner CX23 Ubuntu server and recorded its current resources and location.
2. Recovered Ubuntu root access from Rescue after the Hetzner web console did not paste the password with `Cmd+V`; the Rescue keyboard used Finnish layout. The exact recovery sequence and key positions are in [rescue.md](rescue.md).
3. Changed the Ubuntu root password from the logged-in Ubuntu root shell. The secret value is not recorded.
4. Verified the SSH host fingerprint, installed the Mac's public key for root, and successfully tested a new key-based SSH connection.
5. Inspected UFW, Docker/Compose, listening ports, Hetzner Cloud Firewalls and provider backups. Current results are listed above.

## Recommended management split

The proposed split is sound for this server. Because it currently has no application data, there is still a straightforward opportunity to adopt the existing VPS into OpenTofu now. Importing preserves the server and its current IPs; it does not create a new server or automatically generate the final configuration. Add matching resource blocks, import the existing resource IDs, then review `tofu plan` for any proposed replacement or unrelated changes before applying. Recreating from OpenTofu is also possible, but needs a deliberate IP-retention decision and a rebuild; it is not required just to gain reproducibility.

| Tool | Responsibility | Appropriate use here |
| --- | --- | --- |
| OpenTofu + Hetzner provider | Cloud resources: server, IPs, networks, Cloud Firewall, labels and backup settings | Import/adopt the existing server and any separately managed primary IPs into reviewed state. Review every plan for replacement/deletion before apply. Keep state private; it can contain sensitive values. |
| cloud-init | One-time first-boot bootstrap | On a future creation/rebuild, create a limited admin account and install its public SSH key. Keep bootstrap small; it is not the ongoing configuration manager. |
| Ansible | Repeatable host configuration | Install security updates, create users and sudo policy, harden SSH, configure the host firewall, install Docker/Compose, prepare directories and logging. Prefer idempotent modules and validate each playbook before applying. |
| Docker Compose | Per-application runtime and data wiring | Keep app services, internal networks and persistent volumes in the relevant app repository. Publish only the reverse proxy's intended public ports; keep PostgreSQL private. |

Ansible is appropriate for repeatable configuration because its modules generally check whether the target state is already in place. Idempotency is a property to verify in each playbook, not an automatic guarantee for arbitrary shell commands. OpenTofu also tracks state: never put its state in Git, and treat it as sensitive. The Hetzner provider documents that `user_data` is cloud-init input and that changing injected SSH-key selections can require server replacement; account for the already-running server before managing those fields.

The existing Hetzner API token is read-only. Keep using it for inventory and read-only planning. Create a separate project-scoped Read & Write token only when a reviewed OpenTofu plan is ready to change Hetzner resources; load it through the environment/password manager, not source files. The token value itself is not recorded here. State can contain sensitive resource attributes even when provider credentials are supplied separately.

For the first security baseline, configure the **Hetzner Cloud Firewall** as the public ingress boundary. Do not add custom outbound rules initially: Hetzner changes outbound traffic to implicit deny when custom egress rules are present. Determine the SSH source policy before applying ingress rules. The current server allows root password SSH, so do not expose port 22 broadly until password login is disabled or SSH is restricted to a trusted source. Add public TCP 80/443 only when the reverse proxy and applications are ready. Never publish PostgreSQL port 5432 publicly.

Docker's published ports can bypass UFW rules, so do not rely on UFW alone to protect published containers. Enforce public ingress at the Hetzner firewall and restrict Compose port publishing to the reverse proxy; if host-level filtering is also needed, design it with Docker's packet-filtering behavior in mind.

## Deployment and rollback

No application deployment or rollback procedure is active yet. The workspace design proposes building immutable images in CodeFloe, recording each digest, and deploying the same tested digest through Docker Compose. The application repositories should own their `Dockerfile`, Compose definition and safe configuration examples. Keep runtime secrets outside Git and images. Before a release, back up persistent data; check health and preserve the previous image digest for application rollback. Database migrations need a separate compatibility and recovery plan.

## Configuration and secrets

- Keep the Hetzner API token in Proton Pass and the local `hcloud` CLI context. The token value is not recorded.
- Keep the root password in Proton Pass; do not copy it into this document, cloud-init, Ansible variables, OpenTofu state or shell history.
- Keep the Mac private SSH key at its existing local path. Only the public key belongs on the server.
- Future Ansible secrets should use a protected secret mechanism (for example, Ansible Vault or controlled runtime injection). Do not commit vault passwords.
- Future app secret names and safe defaults belong in each app repository; values belong in the password manager/runtime.

## Backup and restore

- **Current state:** Hetzner backups are disabled; no application data exists yet.
- **Target:** versioned, consistent PostgreSQL exports and required persistent files copied encrypted to the Synology over a private route, with independent retention and failure alerts.
- **Restore:** restore to an isolated target first; verify database integrity and an application read/write check before any production replacement.
- **Trial:** none has been performed. Do not claim recoverability until a restore has succeeded and its date/evidence are recorded.

## Outstanding work

Track remaining work in the [Hetzner TODO](../TODO.md), which is the canonical checklist for this environment.

## References

- [Architecture](../../architectuur_codefloe_synology_hetzner.md)
- [Implementation plan](../../implementatieplan_codefloe_synology_hetzner.md)
- [Hetzner Cloud Firewall behavior](https://docs.hetzner.com/cloud/firewalls/faq/)
- [Hetzner Cloud provider server resource](https://registry.terraform.io/providers/hetznercloud/hcloud/latest/docs/resources/server)
- [OpenTofu provider versions and lock file](https://opentofu.org/docs/language/providers/)
- [OpenTofu sensitive state](https://opentofu.org/docs/language/state/sensitive-data/)
- [Ansible idempotency](https://docs.ansible.com/projects/ansible-core/2.13/user_guide/playbooks_intro.html)
- [Docker and host firewall behavior](https://docs.docker.com/engine/network/packet-filtering-firewalls/)
- [Docker Compose](https://docs.docker.com/compose/)
