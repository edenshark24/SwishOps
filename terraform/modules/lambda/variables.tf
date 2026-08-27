variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "swishops-nba-data-fetcher"
}

variable "lambda_role_arn" {
  description = "ARN of the IAM role for Lambda execution (from iam module)"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for Lambda VPC config"
  type        = list(string)
}

variable "lambda_security_group_id" {
  description = "Security group ID to attach to the Lambda ENI"
  type        = string
}

variable "nba_api_key_secret_arn" {
  description = "ARN of the NBA API key secret in Secrets Manager"
  type        = string
}

variable "db_password_secret_arn" {
  description = "ARN of the DB password secret in Secrets Manager"
  type        = string
}

variable "db_host" {
  description = "RDS endpoint address"
  type        = string
}

variable "schedule_expression" {
  description = "EventBridge schedule for triggering the fetch"
  type        = string
  default     = "rate(6 hours)"
}
