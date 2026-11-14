terraform {
  required_version = ">= 1.8.0"

  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.70"
    }
  }
}

# Token comes from the HCLOUD_TOKEN environment variable, never from a file in Git.
provider "hcloud" {}
