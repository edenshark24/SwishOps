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
variable "public_subnet_cidrs" {
  description = "subnet for public access"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}
variable "private_subnet_cidrs" {
  description = "subnet for private access"
  type        = list(string)
  default     = ["10.0.3.0/24", "10.0.4.0/24"]
}
