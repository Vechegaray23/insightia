// variables.tf

variable "supabase_organization_id" {
  description = "ID de la organización en Supabase"
  type        = string
}

variable "supabase_project_name" {
  description = "Nombre del proyecto en Supabase"
  type        = string
  default     = "mvp-project"
}

variable "supabase_region" {
  description = "Región del proyecto Supabase"
  type        = string
  default     = "us-east-1"
}

variable "supabase_site_url" {
  description = "URL pública del proyecto Supabase"
  type        = string
  default     = "http://localhost"
}

variable "supabase_access_token" {
  description = "Token de acceso a la API de Supabase"
  type        = string
}

variable "cloudflare_account_id" {
  description = "Account ID de Cloudflare"
  type        = string
}

variable "cloudflare_api_token" {
  description = "API Token de Cloudflare"
  type        = string
}

variable "railway_project_name" {
  description = "Nombre del proyecto en Railway"
  type        = string
  default     = "mvp-project"
}

variable "railway_token" {
  description = "Token de acceso a Railway"
  type        = string
}

variable "repo" {
  description = "URL del repositorio Git"
  type        = string
  default     = "https://github.com/example/repo"
}

variable "branch" {
  description = "Rama por defecto para CI/CD"
  type        = string
  default     = "main"
}
