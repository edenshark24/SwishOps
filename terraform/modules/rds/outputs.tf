output "db_endpoint" {
  description = "endpoint of rds"
  value       = aws_db_instance.main.endpoint
}
output "db_address" {
  description = "hostname of rds, without port"
  value       = aws_db_instance.main.address
}
output "db_name" {
  description = "name of rds"
  value       = var.db_name
}
