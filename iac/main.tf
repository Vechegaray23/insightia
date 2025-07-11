terraform {
  required_version = ">= 1.8, < 1.9"
  required_providers {
    supabase = {
      source  = "supabase/supabase"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "4.24.0"
    }
    railway = {
      source = "railwayapp/railway"
    }
  }
}

module "supabase" {
  source = "./modules/supabase"
}

module "r2" {
  source = "./modules/cloudflare_r2"
}

module "railway" {
  source = "./modules/railway_project"
  name   = var.railway_project_name
}

