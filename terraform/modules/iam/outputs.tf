output "eks_cluster_role_arn" {
  description = "arn of cluster role"
  value       = aws_iam_role.eks_cluster.arn
}
output "eks_node_group_role_arn" {
  description = "node group arn role"
  value       = aws_iam_role.eks_node_group.arn
}
output "lambda_role_arn" {
  description = "lambda arn role"
  value       = aws_iam_role.lambda.arn
}
