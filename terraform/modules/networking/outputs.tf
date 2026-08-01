output "vpc_id" {
  description = "id of vpc"
  value       = aws_vpc.main.id
}
output "public_subnet_ids" {
  description = "id of public subnets"
  value       = aws_subnet.public[*].id
}
output "private_subnet_ids" {
  description = "id of private subnets"
  value       = aws_subnet.private[*].id
}
