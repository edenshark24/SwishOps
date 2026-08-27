terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.31.0"
    }
  }

  backend "s3" {
    bucket         = "swishops-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "swishops-terraform-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}

module "networking" {
  source       = "./modules/networking"
  project_name = var.project_name
  environment  = var.environment
}

module "iam" {
  source                 = "./modules/iam"
  project_name           = var.project_name
  environment            = var.environment
  db_password_secret_arn = module.secrets.db_password_arn
  nba_api_key_secret_arn = module.secrets.nba_api_key_arn
}

module "ecr" {
  source       = "./modules/ecr"
  project_name = var.project_name
  environment  = var.environment
}

module "eks" {
  source                  = "./modules/eks"
  project_name            = var.project_name
  environment             = var.environment
  vpc_id                  = module.networking.vpc_id
  private_subnet_ids      = module.networking.private_subnet_ids
  eks_cluster_role_arn    = module.iam.eks_cluster_role_arn
  eks_node_group_role_arn = module.iam.eks_node_group_role_arn
}

module "rds" {
  source             = "./modules/rds"
  project_name       = var.project_name
  environment        = var.environment
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  db_name            = var.db_name
  db_username        = var.db_username
  db_password        = var.db_password
}

module "secrets" {
  source       = "./modules/secrets"
  project_name = var.project_name
  environment  = var.environment
  db_password  = var.db_password
  nba_api_key  = var.nba_api_key
}

module "lambda" {
  source = "./modules/lambda"

  lambda_role_arn          = module.iam.lambda_role_arn
  private_subnet_ids       = module.networking.private_subnet_ids
  lambda_security_group_id = module.networking.nodes_security_group_id
  nba_api_key_secret_arn   = module.secrets.nba_api_key_arn
  db_password_secret_arn   = module.secrets.db_password_arn
  db_host                  = module.rds.db_endpoint
}
