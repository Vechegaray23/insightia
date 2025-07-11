variable "organization_id" {
  type = string
}

variable "project_name" {
  type = string
  default = "mvp-project"
}

variable "supabase_region" {
  type = string
  default = "us-east-1"
}

variable "site_url" {
  type = string
  default = "http://localhost"
}

variable "cloudflare_account_id" {
  type = string
}

variable "render_name" {
  type = string
  default = "mvp-service"
}

variable "render_region" {
  type = string
  default = "oregon"
}

variable "render_env" {
  type = string
  default = "docker"
}

variable "repo" {
  type = string
  default = "https://github.com/example/repo"
}

variable "branch" {
  type = string
  default = "main"
}
