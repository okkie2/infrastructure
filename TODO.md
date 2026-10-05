# TODO

What is planned for the NAS and its documentation. Project-specific lists live in each project (for example [gluetun-qbittorrent](projects/gluetun-qbittorrent/TODO.md)); the wider checklist is [host → Open items](projects/host/README.md#open-items-2026-10-05).

## NEXT

- [ ] **Save the Radarr login and delete the file.** The generated password is in `~/radarr-login.txt` on the NAS (mode 600). Read it with `ssh ok040 cat radarr-login.txt`, store it in your password manager, then delete it with `ssh ok040 rm radarr-login.txt`.
- [ ] **Read the first extended SMART test result.** It was started 2026-10-05 at 15:51 and takes about 13 hours (due around 05:00 the next morning). Read it with `ssh ok040 'sudo smartctl -d sat -l selftest /dev/sata1'`; see [host → Scheduled tasks](projects/host/README.md#scheduled-tasks-control-panel--task-scheduler).
- [ ] **Decide on the firewall deny rule.** The DSM firewall is on but has no deny rule; the recommended rule set and the test checklist are in [host → Network and services](projects/host/README.md#network-and-services).
- [ ] **Add a third copy for Immich** (a USB drive and/or an encrypted cloud copy), and **decide on encrypting the OK035 backups**. The reasoning and the plan are in [immich → Backups](projects/immich/README.md#backups) and [host → Backups](projects/host/README.md#backups).
