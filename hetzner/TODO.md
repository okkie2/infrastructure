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
ai:
  involvement: drafting
  description: "Earlier authorship is not recorded. Claude Code updated the completion state and added follow-ups on 14 November 2026."
updated: "2026-11-14"
updated_by: "Claude Code (Opus 5.5)"
update_reason: "Marked provisioning items done after live verification; added follow-ups from the provisioning and from the QA and security reviews (rebuild, patching and supply chain); recorded the provisioning token revocation."
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

- [ ] Nightly `pg_dump` per app database, plus the Caddy data volume.
- [ ] Encrypted transport over Tailscale to the Synology, in an append-only or pull model so a compromised VPS cannot delete backups. This needs a narrow tailnet grant from `tag:hetzner-prod` to the backup target only.
- [ ] Retention, failure alerting, and an isolated restore trial with recorded evidence.
- **Done when:** a restore from the Synology to a clean target succeeds and its date and evidence are recorded in operations.

### 2. Require a sudo password

- [ ] Set a password for `joost` (Proton Pass), replace the `NOPASSWD` sudoers entry, and run Ansible with `--ask-become-pass`.
- **Done when:** `sudo -n true` fails, `sudo -v` with the password works, and the playbook still reaches `changed=0`.

### 3. Protect OpenTofu state

- [ ] `hetzner/opentofu/terraform.tfstate` exists only on the Mac (FileVault on). Confirm it is in an encrypted backup such as Time Machine, or move to a remote locked backend before using a second machine.
- **Done when:** a backup copy of the state is confirmed restorable.

### 4. Revoke the provisioning token

- [x] The owner deleted the read-write token `opentofu-hetzner-prod` on 14 November 2026. The read-only `hcloud` context still works. Create a new short-lived read-write token per apply and delete it afterwards.

### 5. First app

- [ ] Follow [Add an app](apps.md), including opening public web (`public_web_enabled`) and the Caddy ACME email.
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
