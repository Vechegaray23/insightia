terraform {
  required_providers {
    supabase = {
      source  = "supabase/supabase"
      version = ">= 0.11.1"
    }
  }
}

provider "supabase" {
  access_token = var.access_token
}

resource "supabase_project" "this" {
  organization_id   = var.organization_id
  name              = var.project_name
  region            = var.region
  database_password = var.db_password
}

resource "supabase_auth_config" "this" {
  project_id = supabase_project.this.id
}
