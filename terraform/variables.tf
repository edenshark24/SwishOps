variable "project_name" {
  description = "name for the project"
  type        = string
}
variable "environment" {
  description = "the environment of the project"
  type        = string
}
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}
variable "aws_region" {
  description = "region on which the project is built on"
  type        = string
  default     = "us-east-1"
}
