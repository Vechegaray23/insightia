terraform {
  required_providers {
    render = {
      source  = "renderinc/render"
      version = ">= 0.7.2"
    }
  }
}

provider "render" {
  api_key = var.api_key
}

resource "render_service" "hello" {
  name         = var.service_name
  service_type = "web_service"
  branch       = "main"
  env          = "docker"
  healthcheck_path = "/"
}
