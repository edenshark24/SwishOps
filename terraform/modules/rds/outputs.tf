output "db_endpoint" {
  description = "endpoint of rds"
  value       = aws_db_instance.main.endpoint
}
output "db_name" {
  description = "name of rds"
  value       = var.db_name
}
