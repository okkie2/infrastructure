# Hetzner

Server-specific operations live under each server's name. Configuration as code lives next to them. The workspace-level architecture and implementation plans cover both Hetzner and Synology:

- [ubuntu-4gb-hel1-1](ubuntu-4gb-hel1-1/): operations record, runbook, rescue procedure
- [Add an app](apps.md): onboard a containerised app with its own PostgreSQL database
- [opentofu/](opentofu/): Hetzner resources (server, primary IPs, Cloud Firewall)
- [ansible/](ansible/): host configuration (admin user, Tailscale, SSH hardening, Docker, Caddy and PostgreSQL platform)
- [Hetzner TODO](TODO.md)
- [Architecture](../architectuur_codefloe_synology_hetzner.md)
- [Implementation plan](../implementatieplan_codefloe_synology_hetzner.md)
