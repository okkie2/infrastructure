# tailscale-access

How the NAS devices are reached over Tailscale, and why a device can be "online" yet unreachable. The policy itself lives in the Tailscale admin console (Access controls), not in this repo; this note records the parts that matter here.

## Devices

| Device | Tailscale IP | Role |
|---|---|---|
| OK040 | `100.126.55.95` | The home NAS (Container Manager projects in this repo). |
| OK035 | `100.74.138.41` (`ok035.tail4d7938.ts.net`) | Remote backup target (Synology, DSM 7, Tailscale 1.58.2, key expiry disabled). Runs in userspace networking (TUN Mode: No). |

## Access policy

Tailscale denies everything not explicitly granted. OK035 is deliberately locked down: only OK040's gateway may reach it, and only on the backup port and SSH.

```json
// OK040's gateway may only reach OK035, only on the backup port + SSH
{ "src": ["100.126.55.95"], "dst": ["100.74.138.41"], "ip": ["6281", "22"] }
```

Your own devices have no grant to OK035. Opening `http://100.74.138.41:5000` (DSM) from a laptop therefore times out, and the device page in the Tailscale console says: *"The current tailnet policy file does not allow connecting to this device."* The firewall, DSM and the NAS are not at fault.

## Reaching DSM on OK035

Add a grant for the admin UI (and SSH if wanted):

```json
// You may open DSM on OK035 (admin UI only)
{ "src": ["joost.okkinga@gmail.com"], "dst": ["100.74.138.41"], "ip": ["5000", "5001", "22"] }
```

- `5000` is DSM over HTTP, `5001` over HTTPS. Drop `22` if SSH from your own devices is not needed.
- This leaves the gateway rule unchanged, so the backup path stays as restricted as before.
- Check with **Preview rules** in the ACL editor before saving.

Status: this grant is recommended, not recorded as applied. Update this line once it is in the policy.

## If it still fails after the grant

- **Synology firewall:** allow `100.64.0.0/10` to port 5000 (Control Panel → Security → Firewall).
- **Userspace networking:** inbound access to the NAS's own services normally works; if not, enable TUN mode with `sudo /var/packages/Tailscale/target/bin/tailscale configure-host` and restart the Tailscale package.
- **Source device:** make sure Tailscale is connected on the machine you browse from.
- **SSH:** the policy's `ssh` block only covers `autogroup:self`; a tagged or otherwise non-self device may need its own `dst`.
