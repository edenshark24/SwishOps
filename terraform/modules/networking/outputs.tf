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

output "nodes_security_group_id" {
  description = "Security group ID for EKS nodes / workloads"
  value       = aws_security_group.eks_nodes.id
}

output "rds_security_group_id" {
  description = "Security group ID for RDS database"
  value       = aws_security_group.rds.id
}
