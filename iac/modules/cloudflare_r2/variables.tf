variable "api_token" {
  description = "Cloudflare API token"
  type        = string
  sensitive   = true
}

variable "account_id" {
  description = "Cloudflare account ID"
  type        = string
}

variable "kms_key_id" {
  description = "ID of the KMS key used to encrypt objects"
  type        = string
}
