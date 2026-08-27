variable "project_name" {
  description = "name for the project"
  type        = string
}
variable "environment" {
  description = "the environment of the project"
  type        = string
}

variable "db_password_secret_arn" {
  description = "ARN of the DB password secret"
  type        = string
}

variable "nba_api_key_secret_arn" {
  description = "ARN of the NBA API key secret"
  type        = string
}
