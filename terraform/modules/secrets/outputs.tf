output "db_password_arn" {
  description = "arn of db password"
  value       = aws_secretsmanager_secret.db_password.arn
}
output "nba_api_key_arn" {
  description = "arn of nba api key"
  value       = aws_secretsmanager_secret.nba_api_key.arn
}
