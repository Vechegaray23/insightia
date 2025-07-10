output "service_id" {
  description = "ID of the Render service"
  value       = render_service.hello.id
}

output "service_name" {
  description = "Name of the Render service"
  value       = render_service.hello.name
}
