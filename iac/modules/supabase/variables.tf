variable "organization_id" {
  type = string
}

variable "name" {
  type = string
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "database_password" {
  type      = string
  sensitive = true
}
