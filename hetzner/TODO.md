# Hetzner TODO

Canonical follow-up list for Hetzner infrastructure. Keep each item here until its done condition is verified; server operations documents link here instead of duplicating status.

## 1. Version the infrastructure source

- [ ] Create a dedicated Git repository for `hetzner/` or a clearly scoped repo root.
- [ ] Add the architecture/operations docs and future OpenTofu/Ansible files.
- [ ] Confirm secrets, private keys, local OpenTofu state and generated files are excluded and not tracked.
- **Done when:** the repo has a remote and a clean, reviewable change history; no secret values or state files are in Git.

## 2. Secure and verify SSH administration

- [ ] Choose the intended SSH access path: trusted source-IP restriction, a private overlay such as Tailscale, or key-only public SSH.
- [ ] Create a named non-root administrator with sudo and install its public key.
- [ ] Verify a second SSH login as that administrator before changing root access or password authentication.
- [ ] Disable root SSH login and SSH password authentication after the replacement access path is tested.
- **Done when:** a fresh non-root key-based SSH session works and the effective SSH configuration confirms the intended root/password policy.

## 3. Configure the Hetzner Cloud Firewall

- [ ] Choose SSH source ranges, including IPv4 and IPv6 behavior.
- [ ] Apply a default-deny inbound policy allowing only the selected SSH source initially; keep outbound rules unset.
- [ ] Add public TCP 80/443 only when the reverse proxy and applications are ready.
- [ ] Verify SSH access in a second session and verify the effective Cloud Firewall attachment before closing the existing session.
- **Done when:** inbound exposure matches the approved design, SSH remains reachable through the chosen path, and PostgreSQL is not publicly reachable.

## 4. Adopt infrastructure into OpenTofu

- [ ] Import the existing server and any separately managed primary IP resources into OpenTofu state; the VPS is currently empty, so there is no application data to migrate.
- [ ] Verify FileVault and secure encrypted backups before using local OpenTofu state; exclude state and plan files from Git. Revisit a remote locked backend before multi-machine or automated runs.
- [ ] Pin the Hetzner provider and commit its lock file.
- [ ] Review the import plan and subsequent plan for replacement, deletion, IP changes and firewall changes before any apply.
- [ ] Create a separate project-scoped Read & Write Hetzner API token only when a reviewed plan is ready to apply; keep it in Proton Pass and out of source files.
- **Done when:** a reviewed plan has no unintended replacement/deletion and state recovery/access is documented.

## 5. Configure the host with Ansible

- [ ] Create an inventory and playbooks for users/SSH, updates, host firewall strategy, Docker Engine/Compose, logging and deployment directories.
- [ ] Keep secrets out of plain inventory and source control.
- [ ] Use state-aware modules where possible; test check mode and repeat the playbook to confirm a no-change second run.
- **Done when:** a reviewed playbook establishes the intended host state, succeeds twice, and a second run reports no unexpected changes.

## 6. Prepare applications and recovery

- [ ] Keep each app's Dockerfile and Compose definition in its application repository; publish only the reverse proxy's public ports.
- [ ] Configure external encrypted backups for database dumps and required persistent files.
- [ ] Perform an isolated restore and verify database integrity plus application access before writing production data.
- **Done when:** each app has a pinned deployment artifact, private database networking, working health checks, and a documented successful restore trial.
