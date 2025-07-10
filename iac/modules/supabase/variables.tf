variable "access_token" {
  description = "Supabase personal access token"
  type        = string
}

variable "organization_id" {
  description = "Organization where the project will be created"
  type        = string
}

variable "project_name" {
  description = "Name for the Supabase project"
  type        = string
}

variable "region" {
  description = "Supabase region"
  type        = string
}

variable "db_password" {
  description = "Password for the PostgreSQL database"
  type        = string
  sensitive   = true
}
