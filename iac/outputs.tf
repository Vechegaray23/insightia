output "supabase_project_id" {
  value = module.supabase.project_id
}

output "audio_bucket" {
  value = module.r2.audio_bucket
}

output "exports_bucket" {
  value = module.r2.exports_bucket
}

output "railway_project_id" {
  value = module.railway.project_id
}
