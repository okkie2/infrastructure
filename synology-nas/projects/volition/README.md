# Volition notes and ChatGPT Voice tunnel

Checked against OK040 on 2026-10-20. Volition stores Joost's notes as plain Markdown and exposes them over the Model Context Protocol (MCP). ChatGPT's custom **Volition** app uses the MCP for note operations.

| Container | Image | Purpose |
|---|---|---|
| `volition` | `ghcr.io/okkie2/volition@sha256:ab0c5956db21b7758538959b53812a39627efe9d1a99f2fdaf22d4c7aa413a20` | Serves MCP at `http://100.126.55.95:8766/mcp`; port 8766 is bound to the NAS's Tailscale address only. |
| `volition-tunnel-client` | `ghcr.io/openai/tunnel-client:latest` (observed image digest `sha256:4605ea909701668d3bdcbe6152558e068e24006aa96ca5518ca67f786a1bce13`) | Keeps an outbound connection to OpenAI Secure MCP Tunnel and forwards ChatGPT requests to the private Volition MCP server. It has no published host port. |

The notes live at `/volume1/homes/joost/Volition/notes`, mounted read-write at `/notes`. MCP writes are committed to the store's local Git history; the notes repository has no Git remote. The daily `Volition Daily Copy` task backs up the store, including `.git`, outside the notes directory.

The tunnel client runs on the separate `volition-tunnel-egress` Docker bridge network (`172.24.0.0/24`); Volition runs on Docker's default bridge. The client has no host-published port. It mounts its YAML config and both credentials read-only. The two credentials are `openai-runtime-key`, which authenticates the client to OpenAI, and `volition-authorization`, which is sent as the `Authorization` header to Volition. Secret values are kept under `/volume1/homes/master/volition-deploy/secrets/` and are not in this repository. On 2026-10-20 the deployment directory and secrets directory were mode `0700`, and the environment/config/credential files were mode `0600`, all owned by `master:users`. The OpenAI runtime key expires on 2027-10-19.

The Volition HTTP app requires exactly one `Authorization: Bearer …` header on every route except `/health`; it compares the token in constant time and rejects missing or mismatched tokens with HTTP 401. The token must be at least 32 ASCII characters with no whitespace. DNS-rebinding protection is enabled with allowed hosts/origins derived from loopback and the configured publish host. The active MCP server exposes two tools: `query` (catalogue, folder, document, and search reads) and `capture` (create or edit a Markdown document); it exposes no shell or general filesystem tool. One shared bearer token authorizes both tools; there is no per-tool or per-user authorization. `query` is marked read-only; `capture` has idempotent retry support and expected-revision checking for edits.

Both containers run as non-root numeric users with read-only root filesystems, all Linux capabilities dropped, and `no-new-privileges`. Volition has a 512 MB memory limit; its only writable bind mount is the notes store at `/notes` (it also has a 32 MB writable `/tmp` tmpfs). Although the deployment script specifies a 128-process limit, the live container inspection reported no active PID limit. The tunnel client mounts only its config and credential files read-only and uses a 16 MB no-exec, no-suid `/tmp`.

**Egress filtering is not confirmed.** The tunnel Compose file says a persistent egress policy must be installed, but the read-only firewall check on 2026-10-20 found `DOCKER-USER` containing only `RETURN`. No container-specific egress allow-list was visible in that chain. Treat outbound restriction as an unresolved deployment control until the effective firewall policy is reviewed and enforced. The tunnel client uses the mutable `latest` tag and Watchtower applies its updates every six hours; the digest above records the image observed on 2026-10-20, not a pinned deployment reference.

Watchtower's live target list includes `volition-tunnel-client`; the digest-pinned Volition server is not in that list and is updated through the deployment script. Both containers were running on 2026-10-20. Mobile ChatGPT Live Voice had successfully queried Volition on 2026-10-19.

## Deployment reference

The redacted deployment and recovery files are included in [`deployment/`](deployment/). They were copied from `/volume1/homes/master/volition-deploy` on 2026-10-20; `tunnel-client.yaml.example` redacts the tunnel identifier, and `volition.env.example` contains placeholders only. They are a reviewable reference, not an instruction to deploy. The active secret values remain on the NAS and are not copied here. See [`deployment/README.md`](deployment/README.md) for capture scope, differences from the observed runtime, and update/recovery notes.
