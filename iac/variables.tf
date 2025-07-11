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

variable "railway_project_name" {
  type    = string
  default = "mvp-project"
}
variable "railway_token" {
  type = string
}


variable "repo" {
  type = string
  default = "https://github.com/example/repo"
}

variable "branch" {
  type = string
  default = "main"
}
