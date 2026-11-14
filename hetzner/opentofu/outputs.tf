output "server_ipv4" {
  value = hcloud_primary_ip.ipv4.ip_address
}

output "server_ipv6_network" {
  value = hcloud_primary_ip.ipv6.ip_network
}
