variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "sentinelgrid-eks"
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version"
  type        = string
  default     = "1.30"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "azs" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "private_subnets" {
  description = "Private subnet CIDRs"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnets" {
  description = "Public subnet CIDRs"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

variable "node_group_general" {
  description = "General node group settings"
  type = object({
    min_size       = number
    max_size       = number
    desired_size   = number
    instance_types = list(string)
    capacity_type  = string
  })
  default = {
    min_size       = 1
    max_size       = 3
    desired_size   = 1
    instance_types = ["t3.medium"]
    capacity_type  = "ON_DEMAND"
  }
}

variable "external_dns_domain_filters" {
  description = "Domain filters for external-dns"
  type        = list(string)
  default     = []
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.medium"
}

variable "rds_username" {
  description = "RDS master username"
  type        = string
  default     = "sg"
}

variable "rds_password" {
  description = "RDS master password (provide via tfvars/secret manager)"
  type        = string
  sensitive   = true
  nullable    = false
}

variable "rds_db_name" {
  description = "RDS database name"
  type        = string
  default     = "sg"
}

variable "os_instance_type" {
  description = "OpenSearch instance type"
  type        = string
  default     = "t3.small.search"
}

variable "os_instance_count" {
  description = "OpenSearch instance count"
  type        = number
  default     = 2
}

variable "os_volume_size" {
  description = "OpenSearch volume size (GB)"
  type        = number
  default     = 50
}
