terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = ">= 4.0"
    }
  }
}

provider "cloudflare" {
  api_token = var.api_token
}

resource "cloudflare_r2_bucket" "audio" {
  account_id = var.account_id
  name       = "audio"
  kms_key_id = var.kms_key_id
}

resource "cloudflare_r2_bucket" "exports" {
  account_id = var.account_id
  name       = "exports"
  kms_key_id = var.kms_key_id
}

resource "cloudflare_r2_bucket_lifecycle" "audio" {
  account_id = var.account_id
  bucket     = cloudflare_r2_bucket.audio.name

  rule {
    status = "Enabled"

    expiration {
      days = 90
    }
  }
}

resource "cloudflare_r2_bucket_lifecycle" "exports" {
  account_id = var.account_id
  bucket     = cloudflare_r2_bucket.exports.name

  rule {
    status = "Enabled"

    expiration {
      days = 90
    }
  }
}
