locals {
  location = "hel1"
  labels = {
    environment = "prod"
    managed_by  = "opentofu"
  }
}

resource "hcloud_primary_ip" "ipv4" {
  name     = "primary_ip-161396837"
  type     = "ipv4"
  location = local.location
  # Keep the public address if the server is ever deleted or rebuilt.
  auto_delete       = false
  delete_protection = true
  labels            = local.labels

  lifecycle {
    prevent_destroy = true
    # The server owns the assignment; OpenTofu must never unassign the address.
    ignore_changes = [assignee_id, assignee_type]
  }
}

resource "hcloud_primary_ip" "ipv6" {
  name              = "primary_ip-161396838"
  type              = "ipv6"
  location          = local.location
  auto_delete       = false
  delete_protection = true
  labels            = local.labels

  lifecycle {
    prevent_destroy = true
    # The server owns the assignment; OpenTofu must never unassign the address.
    ignore_changes = [assignee_id, assignee_type]
  }
}

resource "hcloud_server" "prod" {
  name        = "ubuntu-4gb-hel1-1"
  server_type = "cx23"
  image       = "ubuntu-26.04"
  location    = local.location
  labels      = local.labels
  backups     = false

  delete_protection  = true
  rebuild_protection = true

  # The existing primary IPs (above) are assigned to this server. public_net is a
  # creation-time input and is not managed here, so OpenTofu never re-plumbs addresses.

  lifecycle {
    prevent_destroy = true
    # Creation-time inputs: changing them would force a new server.
    ignore_changes = [image, user_data, ssh_keys, public_net]
  }
}

resource "hcloud_firewall" "prod" {
  name   = "prod-ingress"
  labels = local.labels

  # No SSH rule: administration goes over Tailscale only.

  rule {
    description = "ICMP (ping, path MTU)"
    direction   = "in"
    protocol    = "icmp"
    source_ips  = ["0.0.0.0/0", "::/0"]
  }

  dynamic "rule" {
    for_each = var.tailscale_direct_udp_enabled ? [1] : []
    content {
      description = "Tailscale direct connections"
      direction   = "in"
      protocol    = "udp"
      port        = "41641"
      source_ips  = ["0.0.0.0/0", "::/0"]
    }
  }

  dynamic "rule" {
    for_each = var.public_web_enabled ? [
      { protocol = "tcp", port = "80" },
      { protocol = "tcp", port = "443" },
      { protocol = "udp", port = "443" },
    ] : []
    content {
      description = "Caddy ${upper(rule.value.protocol)} ${rule.value.port}"
      direction   = "in"
      protocol    = rule.value.protocol
      port        = rule.value.port
      source_ips  = ["0.0.0.0/0", "::/0"]
    }
  }

  # No outbound rules on purpose: adding any switches Hetzner to implicit outbound deny.
}

resource "hcloud_firewall_attachment" "prod" {
  count = var.attach_firewall ? 1 : 0

  firewall_id = hcloud_firewall.prod.id
  server_ids  = [hcloud_server.prod.id]
}
