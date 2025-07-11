output "supabase_project_id" {
  value = module.supabase.project_id
}

output "audio_bucket" {
  value = module.r2.audio_bucket
}

output "exports_bucket" {
  value = module.r2.exports_bucket
}

output "render_service_id" {
  value = module.render.service_id
}
