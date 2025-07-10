# Render Module

This Terraform module provisions a simple Render container service named `hello`.
It assumes a Docker-based web service and configures a basic health check.

## Usage

```hcl
module "render" {
  source = "./modules/render"

  api_key      = var.render_api_key
  service_name = "hello"
}
```

The module creates a container service using the Render provider. It expects an
API key with permissions to manage services. The service exposes a basic health
check at the root path.
