# TODO

What is planned for the NAS and its documentation. Project-specific lists live in each project (for example [gluetun-qbittorrent](projects/gluetun-qbittorrent/TODO.md)); the wider checklist is [host → Open items](projects/host/README.md#open-items-2026-10-05).

## NEXT

- [ ] **Start Snapshot Replication and snapshot the `backup` share** (daily, 30 days), then verify it. The package is installed but was stopped on 2026-10-23. This protects the Mac project backups; see [host → Mac project backups](projects/host/README.md#mac-project-backups-convention-2026-10-23).
- [ ] **Finish configuring Bazarr:** turn on subtitle sync, and give movies the `English` profile once Radarr has imported them (`http://100.126.55.95:6767`). Providers and the profile on all series except the Dutch one are done. See [gluetun-qbittorrent → Bazarr](projects/gluetun-qbittorrent/README.md#bazarr-subtitles).
- [ ] **Find a supported way to verify SMART self-test completion.** The drive does not support self-test logging; Task Scheduler records only the asynchronous launch. See [host → Scheduled tasks](projects/host/README.md#scheduled-tasks-control-panel--task-scheduler).
- [ ] **Apply and observe the weekend maintenance plan** in [host → Proposed power and maintenance windows](projects/host/README.md#proposed-power-and-maintenance-windows-not-applied): reconcile daily task times, confirm OK035 availability, update DSM power and Hyper Backup schedules, then compare four completed Sunday runs against the planned margins. Confirm the live qBittorrent deployment and tracker rules before changing its seeding behavior.
- [ ] **Decide on the firewall deny rule.** The DSM firewall is on but has no deny rule; the recommended rule set and the test checklist are in [host → Network and services](projects/host/README.md#network-and-services).
- [ ] **Add a third copy for Immich** (a USB drive and/or an encrypted cloud copy), and **decide on encrypting the OK035 backups**. The reasoning and the plan are in [immich → Backups](projects/immich/README.md#backups) and [host → Backups](projects/host/README.md#backups).
