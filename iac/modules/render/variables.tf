variable "api_key" {
  description = "API key for the Render provider"
  type        = string
  sensitive   = true
}

variable "service_name" {
  description = "Name of the Render service"
  type        = string
  default     = "hello"
}
