terraform {
  required_version = ">= 1.8, < 1.9"
  required_providers {
    supabase = {
      source  = "supabase/supabase"
      version = "0.10.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "4.24.0"
    }
    render = {
      source  = "render-public/render"
      version = "0.6.0"
    }
  }
}

module "supabase" {
  source = "./modules/supabase"
}

module "r2" {
  source = "./modules/cloudflare_r2"
}

module "render" {
  source = "./modules/render_service"
}
