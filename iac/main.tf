terraform {
  required_version = ">= 1.8, < 1.9"
  required_providers {
    supabase = {
      source = "supabase/supabase"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "4.24.0"
    }
    railway = {
      source = "terraform-community-providers/railway"
    }
  }
}
provider "railway" {
  token = var.railway_token
}
provider "supabase" {
  access_token = var.supabase_access_token
}
module "supabase" {
  source          = "./modules/supabase"
  organization_id = var.supabase_organization_id
  name            = var.supabase_project_name
  region          = var.supabase_region
  database_password = var.supabase_db_password
}

module "r2" {
  source     = "./modules/cloudflare_r2"
  account_id = var.cloudflare_account_id

}

module "railway" {
  source = "./modules/railway_project"
  name   = var.railway_project_name
}
provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

