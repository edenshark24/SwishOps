variable "project_name" {
  description = "name for the project"
  type        = string
}
variable "environment" {
  description = "the environment of the project"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID from networking module"
  type        = string
}

variable "db_name" {
  description = "name for db"
  type        = string
}

variable "db_password" {
  description = "password for db"
  type        = string
  sensitive   = true
}

variable "db_username" {
  description = "username for db"
  type        = string
}

variable "private_subnet_ids" {
  description = "private subnet IDs for db"
  type        = list(string)
}

variable "rds_security_group_id" {
  description = "Security group ID for RDS instance"
  type        = string
}
