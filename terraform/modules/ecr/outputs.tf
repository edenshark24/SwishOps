output "repository_urls" {
  description = "url of ecr repos"
  value       = aws_ecr_repository.repos[*].repository_url
}
