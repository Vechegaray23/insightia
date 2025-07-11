terraform {
  required_providers {
    railway = {
      source = "terraform-community-providers/railway"
    }
  }
}

resource "railway_project" "this" {
  name = var.name
}