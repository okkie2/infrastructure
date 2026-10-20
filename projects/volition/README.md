# Volition notes and ChatGPT Voice tunnel

Checked against OK040 on 2026-10-19. Volition stores Joost's notes as plain Markdown and exposes them over the Model Context Protocol (MCP). ChatGPT's custom **Volition** app uses the MCP for note CRUD operations.

| Container | Image | Purpose |
|---|---|---|
| `volition` | `ghcr.io/okkie2/volition@sha256:fac823d498aef02a3ca9a594f1fa900ecb0ddf621d3ad961c749b1668458857d` | Serves MCP at `http://100.126.55.95:8766/mcp`; port 8766 is bound to the NAS's Tailscale address. |
| `volition-tunnel-client` | `ghcr.io/openai/tunnel-client:latest` | Keeps an outbound connection to OpenAI Secure MCP Tunnel and forwards ChatGPT requests to the private Volition MCP server. It has no published inbound port. |

The notes live at `/volume1/homes/joost/Volition/notes`, mounted read-write at `/notes`. MCP writes are committed to the store's local Git history; the notes repository has no Git remote. The daily `Volition Daily Copy` task backs up the store, including `.git`, outside the notes directory.

The tunnel client runs on the `volition-tunnel-egress` Docker network. It uses two separate credentials: `openai-runtime-key` authenticates the client to OpenAI, and `volition-authorization` lets forwarded requests authenticate to Volition. Their values are kept in protected files under `/volume1/homes/master/volition-deploy/secrets/`; they are not in this repository. The OpenAI runtime key expires on 2027-10-19.

Watchtower checks every six hours and its live target list includes `volition-tunnel-client`, so it checks for and applies tunnel-client image updates. The Volition server image is digest-pinned and is not in Watchtower's update list; update it through the Volition deployment procedure. On 2026-10-19 both containers were running. Mobile ChatGPT Live Voice successfully queried Volition that day.

The active deployment files are on the NAS under `/volume1/homes/master/volition-deploy`; this repository does not contain the active Volition Compose file.
