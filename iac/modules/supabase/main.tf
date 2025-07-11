
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
  database_password = var.database_password


}


