# Infrastruture

Personal infrastructure documentation and configuration. This repository brings the Synology NAS and Hetzner Cloud material under one versioned root.

## Areas

- [Hetzner](hetzner/): the cloud VPS, its operations record, recovery procedures and follow-up plan.
- [Synology NAS](synology-nas/): NAS services, Compose projects, host notes and recovery procedures.
- [Architecture](architectuur_codefloe_synology_hetzner.md): cross-system design for Synology TEST and Hetzner PROD.
- [Implementation plan](implementatieplan_codefloe_synology_hetzner.md): phased deployment and operations plan.

## Keep secrets and runtime state out of Git

Do not commit passwords, API tokens, private keys, production data, OpenTofu state or saved plan files. Use the password manager for secrets. Keep environment templates such as `.env.example` in Git and provide real values privately at runtime.
