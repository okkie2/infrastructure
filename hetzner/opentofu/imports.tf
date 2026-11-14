# Adopt the resources created by hand on 9 November 2026. Import does not change them;
# review `tofu plan` for replace/destroy before any apply.
import {
  to = hcloud_primary_ip.ipv4
  id = "161396837"
}

import {
  to = hcloud_primary_ip.ipv6
  id = "161396838"
}

import {
  to = hcloud_server.prod
  id = "175269905"
}
