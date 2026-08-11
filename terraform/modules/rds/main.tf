resource "aws_db_instance" "main" {
  identifier          = "${var.project_name}-${var.environment}-db"
  engine              = "postgres"
  engine_version      = "15.3"
  instance_class      = "db.t3.micro"
  db_name             = var.db_name
  username            = var.db_username
  password            = var.db_password
  db_subnet_group_name = aws_db_subnet_group.main.name
  skip_final_snapshot = true
  publicly_accessible = false
  multi_az            = false

  tags = {
    Name        = "${var.project_name}-${var.environment}-db"
    Environment = var.environment
  }
}
