---
title: "Hetzner TODO"
created: unknown
created_by: unknown
creation_reason: "Canonical follow-up list for Hetzner infrastructure."
purpose: "Track open Hetzner work with verifiable done conditions."
provenance:
  type: original
  description: "Planning list. Completion marks rest on the verified state in ubuntu-4gb-hel1-1/operations.md."
  sources:
    - reference: "ubuntu-4gb-hel1-1/operations.md"
      description: "Evidence for completed items."
    - reference: "../synology-nas/projects/hetzner-backup/README.md"
      description: "Backup design, including the documented unencrypted-storage condition and revisit threshold."
    - reference: "User report in this conversation (2026-11-15)"
      description: "States that QA and security rechecks completed conditionally and that the owner accepts unencrypted storage for current data."
    - reference: "Time Machine settings and tmutil check in this conversation (2026-11-15)"
      description: "The destination is encrypted, backups run through 10:15, and the OpenTofu state path is included; no restore trial was performed at the owner's direction."
ai:
  involvement: drafting
  description: "Earlier authorship is not recorded. Claude Code updated the completion state and added follow-ups on 14 November 2026; Codex recorded backup installation, restore, review, accepted conditions, and OpenTofu state coverage evidence on 15 November 2026."
updated: "2026-11-15"
updated_by: "Claude Code (Fable 5.2)"
update_reason: "Recorded the first app (Kibble) as live and listed the follow-ups from its deployment."
---

# Hetzner TODO

Canonical follow-up list for Hetzner infrastructure. Keep each item here until its done condition is verified. Operations documents link here instead of duplicating status.

## Done (14 November 2026)

- [x] **Version the infrastructure source:** the repository has the remote `okkie2/infrastructure`; state, plans and secrets are ignored.
- [x] **Secure SSH administration:** Tailscale-only, admin `joost`, root and password login disabled, verified with `sshd -T` and refused logins.
- [x] **Cloud Firewall:** `prod-ingress` attached, with no inbound 22 and no outbound rules; public 22 times out.
- [x] **Adopt into OpenTofu:** server and primary IPs imported, provider locked, delete protection on; a follow-up plan shows no changes.
- [x] **Configure the host with Ansible:** two consecutive full runs report `changed=0`.
- [x] **Platform:** Caddy plus shared PostgreSQL deployed; per-app provisioning smoke-tested. See [Add an app](apps.md).

See [operations](ubuntu-4gb-hel1-1/operations.md) for the evidence.

## Open

### 1. Back up to the Synology (owner priority; before any real data)

OK040 fetches the database dumps over Tailscale through a forced command that only lists backups and sends single files; the server gets no access to the NAS. Caddy data is not backed up. Design, decisions and install steps: [hetzner-backup README](../synology-nas/projects/hetzner-backup/README.md). Code: [`ansible/roles/backup`](ansible/roles/backup/).

- [x] Code written and tested locally; QA and security rechecks completed 2026-11-15 and remain conditionally ready due to the documented unencrypted-backup condition. The owner explicitly accepted this condition for current data. Revisit encryption before storing other people's personal data.
- [x] Install: DSM user and pull key, second ntfy topic, Ansible run, NAS script, Task Scheduler entry, status page.
- [x] Isolated restore trial with recorded evidence in [operations](ubuntu-4gb-hel1-1/operations.md#isolated-restore-trial-15-november-2026).
- **Done when:** a restore from the Synology to a clean target succeeds and its date and evidence are recorded in operations.

### 2. Require a sudo password

- [ ] Set a password for `joost` (Proton Pass), replace the `NOPASSWD` sudoers entry, and run Ansible with `--ask-become-pass`.
- **Done when:** `sudo -n true` fails, `sudo -v` with the password works, and the playbook still reaches `changed=0`.

### 3. Protect OpenTofu state

- [x] `hetzner/opentofu/terraform.tfstate` exists only on the Mac. FileVault is on; Time Machine reports an encrypted NAS destination with backups through 15 November 2026 at 10:15, and `tmutil isexcluded` reports the state file as included. The owner accepts the configured backup as usable without a restore trial.
- **Done when:** the encrypted backup is verified and either a restore succeeds or the owner accepts it without a restore trial. Do not use a second machine unless a remote locked backend is configured.

### 4. Revoke the provisioning token

- [x] The owner deleted the read-write token `opentofu-hetzner-prod` on 14 November 2026. The read-only `hcloud` context still works. Create a new short-lived read-write token per apply and delete it afterwards.

### 5. First app

- [x] Kibble went live on 15 November 2026 at `https://wordkibble.com`, following [Add an app](apps.md): public web opened with OpenTofu, the app declared in Ansible, image pinned by digest, private database networking, health check passing. Evidence is in [operations](ubuntu-4gb-hel1-1/operations.md).
- [ ] Follow-ups from this deployment:
  - set `caddy_acme_email` once a contact address exists (parked by the owner);
  - add a route or redirect for `www.wordkibble.com`;
  - done 18 November 2026: IPv6 is on for the networks Caddy publishes from (`default` and each `<app>_edge`), so apps see IPv6 visitors' own addresses;
  - confirm the next NAS pull contains `db-kibble.dump`;
  - decide where private images live: Codefloe makes a public account's packages public, so Kibble's image is built on the host.
- **Done when:** the app is served over HTTPS from a pinned image digest, with private database networking and a working health check.

### 6. Make the rebuild procedure work and rehearse it

- [ ] Implement the outline in [operations](ubuntu-4gb-hel1-1/operations.md#runbook): `public_net` with the protected IPs, bootstrap SSH key, and a temporary source-restricted SSH rule.
- **Done when:** a rebuild onto a throwaway server succeeds following only the documented steps.

### 7. Patching and supply chain

- [ ] Decide on unattended updates for the Docker CE and Tailscale repositories (security pocket only today) and on a kernel reboot policy.
- [ ] Pin Caddy and PostgreSQL images by digest; verify the Docker and Tailscale apt key fingerprints in Ansible.
- **Done when:** the policy is in Ansible and checked by a playbook run.

### 8. Monitoring

- [ ] Alerting for disk, memory, container restarts and backup failures (4 GB RAM is tight for PostgreSQL plus two apps).
- **Done when:** a simulated condition produces an alert the owner receives.
