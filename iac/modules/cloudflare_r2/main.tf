terraform {
  required_providers {
    cloudflare = {
      source = "cloudflare/cloudflare"
    }
  }
}
resource "cloudflare_r2_bucket" "audio" {
  account_id = var.account_id
  name       = "mvp-audio"
}

resource "cloudflare_r2_bucket" "exports" {
  account_id = var.account_id
  name       = "mvp-exports"
}

