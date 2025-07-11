terraform {
  required_providers {
    railway = {
      source = "railwayapp/railway"
    }
  }
}

resource "railway_project" "this" {
  name = var.name
}