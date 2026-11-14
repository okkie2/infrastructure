# TODO

What is planned for the NAS and its documentation. Project-specific lists live in each project (for example [gluetun-qbittorrent](projects/gluetun-qbittorrent/TODO.md)); the wider checklist is [host → Open items](projects/host/README.md#open-items-2026-10-05).

## TODO NOW

- [ ] **Build reusable GitHub Actions → Synology NAS deployment for all projects.** Configure a securely managed self-hosted runner or pull-based deployment agent on OK040, with per-project deployment definitions, scoped credentials/secrets, approval for production, health checks, logging and rollback. First prove the workflow on a noncritical project; then onboard Volition and the other NAS projects. GitHub is the source of truth; actual runner setup and first deployment require NAS access. See [Volition follow-up](https://github.com/okkie2/volition/blob/main/docs/subject-move-next-steps.md).

## NEXT

- [ ] **Kibble: reboot test.** Restart the NAS once and confirm `kibble` and `kibble-ts` come back (port 8770 and Tailscale HTTPS). The remaining Kindle-side checks are in the `kibble` repo's `TODO.md`. See [kibble](projects/kibble/).

- [ ] **Design a voice-started deploy from GitHub to the NAS.** On every car trip a new feature (for example in Volition) is ready but cannot be deployed and used straight away. Investigate how an explicitly approved GitHub Actions workflow, started from ChatGPT Voice, can install a tested release on the NAS without public NAS access: a NAS-initiated pull or an isolated self-hosted runner, with limited credentials, confirmation, a smoke test, an audit log and rollback. Design and security review first; build and enable only after owner approval.
- [ ] **Finish the Mac project backup rollout:** install the weekly LaunchAgent on the Mac and observe its first scheduled run; add an independent NAS-side check that the newest `backup/linkedin-archive/` folder is under 9 days old (or accept manual `./backup.py status`). The first push, restore test and a `backup` snapshot are done; see [host → Mac project backups](projects/host/README.md#mac-project-backups-convention-2026-10-23).
- [ ] **Decide on the firewall deny rule.** The DSM firewall is on but has no deny rule; the recommended rule set and the test checklist are in [host → Network and services](projects/host/README.md#network-and-services).
- [ ] **Add a third copy for Immich** (a USB drive and/or an encrypted cloud copy), and **decide on encrypting the OK035 backups**. The reasoning and the plan are in [immich → Backups](projects/immich/README.md#backups) and [host → Backups](projects/host/README.md#backups).
- [ ] **Find a supported way to verify SMART self-test completion.** The drive does not support self-test logging; Task Scheduler records only the asynchronous launch. See [host → Scheduled tasks](projects/host/README.md#scheduled-tasks-control-panel--task-scheduler).
- [ ] **Apply and observe the weekend maintenance plan** in [host → Proposed power and maintenance windows](projects/host/README.md#proposed-power-and-maintenance-windows-not-applied): reconcile daily task times, confirm OK035 availability, update DSM power and Hyper Backup schedules, then compare four completed Sunday runs against the planned margins. Confirm the live qBittorrent deployment and tracker rules before changing its seeding behavior.
