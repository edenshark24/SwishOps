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

variable "private_subnet_ids" {
  description = "private subnet IDs for worker nodes"
  type        = list(string)
}

variable "eks_cluster_role_arn" {
  description = "ARN of IAM role for EKS cluster"
  type        = string
}

variable "eks_node_group_role_arn" {
  description = "ARN of IAM role for EKS node group"
  type        = string
}

variable "ec2_instance_type" {
  description = "EC2 instance type for worker nodes"
  type        = string
  default     = "t3.medium"
}

variable "node_group_desired_size" {
  description = "desired number of worker nodes"
  type        = number
  default     = 2
}

variable "node_group_min_size" {
  description = "minimum number of worker nodes"
  type        = number
  default     = 1
}

variable "node_group_max_size" {
  description = "maximum number of worker nodes"
  type        = number
  default     = 3
}
