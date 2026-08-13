resource "aws_secretsmanager_secret" "db_password" {
  name = "${var.project_name}/${var.environment}/db_password"
}
resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = var.db_password
}
resource "aws_secretsmanager_secret" "nba_api_key" {
  name = "${var.project_name}/${var.environment}/nba_api_key"
}
resource "aws_secretsmanager_secret_version" "nba_api_key" {
  secret_id     = aws_secretsmanager_secret.nba_api_key.id
  secret_string = var.nba_api_key
}
