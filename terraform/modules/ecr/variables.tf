variable "project_name" {
  description = "name for the project"
  type        = string
}

variable "environment" {
  description = "the environment of the project"
  type        = string
}

variable "repository_names" {
  description = "list of ECR repository names"
  type        = list(string)
  default     = ["frontend", "backend", "ai-service"]
}
