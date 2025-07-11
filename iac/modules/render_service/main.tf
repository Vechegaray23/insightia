terraform {
  required_providers {
    render = {
      source = "render/render"
    }
  }
}
resource "render_service" "app" {
  name       = var.name
  type       = "web_service"
  region     = var.region
  env        = var.env
  repo       = var.repo
  branch     = var.branch
  service_details {
    env        = "docker"
    plan       = "starter"
    env_vars   = {}
    dockerfile_path = "Dockerfile"
  }
}

