output "cluster_name" {
  description = "name of eks cluster"
  value       = aws_eks_cluster.main.name
}
output "cluster_endpoint" {
  description = "eks endpoint"
  value       = aws_eks_cluster.main.endpoint
}
output "cluster_certificate_authority" {
  description = "eks cluster certificate authority"
  value       = aws_eks_cluster.main.certificate_authority[0].data
}
