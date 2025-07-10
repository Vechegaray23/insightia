output "audio_bucket_name" {
  description = "Name of the audio bucket"
  value       = cloudflare_r2_bucket.audio.name
}

output "exports_bucket_name" {
  description = "Name of the exports bucket"
  value       = cloudflare_r2_bucket.exports.name
}
