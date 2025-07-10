output "project_id" {
  description = "ID of the Supabase project"
  value       = supabase_project.this.id
}

output "project_ref" {
  description = "Project reference code"
  value       = supabase_project.this.ref
}
