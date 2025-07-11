output "audio_bucket" {
  value = cloudflare_r2_bucket.audio.name
}

output "exports_bucket" {
  value = cloudflare_r2_bucket.exports.name
}
