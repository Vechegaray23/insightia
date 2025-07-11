resource "cloudflare_r2_bucket" "audio" {
  account_id = var.account_id
  name       = "mvp-audio"
}

resource "cloudflare_r2_bucket" "exports" {
  account_id = var.account_id
  name       = "mvp-exports"
}

output "audio_bucket" {
  value = cloudflare_r2_bucket.audio.name
}

output "exports_bucket" {
  value = cloudflare_r2_bucket.exports.name
}
