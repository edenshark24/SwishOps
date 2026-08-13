variable "project_name" {
  description = "name for the project"
  type        = string
}
variable "environment" {
  description = "the environment of the project"
  type        = string
}
variable "db_password" {
  description = "password for rds"
  type        = string
  sensitive   = true
}
variable "nba_api_key" {
  description = "api key for nba api"
  type        = string
  sensitive   = true
}
