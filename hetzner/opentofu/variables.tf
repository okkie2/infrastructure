variable "attach_firewall" {
  description = "Attach the ingress firewall. It closes public SSH, so keep this false until admin SSH over Tailscale is verified."
  type        = bool
  default     = true
}

variable "public_web_enabled" {
  description = "Open TCP 80/443 and UDP 443 to the internet. Enable only once Caddy and a real domain are ready."
  type        = bool
  default     = false
}

variable "tailscale_direct_udp_enabled" {
  description = "Allow inbound UDP 41641 so Tailscale peers can connect directly instead of through DERP relays."
  type        = bool
  default     = true
}
