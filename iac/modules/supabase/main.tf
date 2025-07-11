
terraform {
  required_providers {
    supabase = {
      source = "supabase/supabase"
    }
  }
}
resource "supabase_project" "this" {
  organization_id = var.organization_id
  name            = var.name
  region          = var.region
  db_version      = "15"
}

resource "supabase_auth_config" "this" {
  project_id = supabase_project.this.id
  site_url   = var.site_url
}


