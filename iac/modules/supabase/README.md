# Supabase Module

This Terraform module provisions a basic Supabase project with database and authentication features enabled.

## Usage

```hcl
module "supabase" {
  source = "./modules/supabase"

  access_token    = var.access_token
  organization_id = var.organization_id
  project_name    = "my-project"
  region          = "us-east-1"
  db_password     = var.db_password
}
```

The module requires a personal access token and organization ID obtained from Supabase. It creates a project, sets the database password, and applies default authentication settings.

Outputs include the project ID and reference code.
