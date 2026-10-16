# Managed data planes (placeholders with sensible defaults).

resource "aws_security_group" "data_plane" {
  name        = "${var.cluster_name}-data-plane"
  description = "Allow EKS nodes to RDS/OpenSearch"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    security_groups = [module.eks.node_security_group_id]
    description     = "Allow from EKS nodes"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# RDS Postgres (pgvector extension supported on Aurora/RDS Postgres >=14)
resource "aws_db_subnet_group" "rds" {
  name       = "${var.cluster_name}-rds-subnets"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_db_instance" "rds_pgvector" {
  identifier              = "${var.cluster_name}-pg"
  engine                  = "postgres"
  engine_version          = "14.11"
  instance_class          = var.rds_instance_class
  allocated_storage       = 50
  db_subnet_group_name    = aws_db_subnet_group.rds.name
  vpc_security_group_ids  = [aws_security_group.data_plane.id]
  username                = var.rds_username
  password                = var.rds_password
  db_name                 = var.rds_db_name
  skip_final_snapshot     = true
  publicly_accessible     = false
  storage_encrypted       = true
  deletion_protection     = false
  multi_az                = false
}

# AWS OpenSearch Service (managed)
resource "aws_opensearch_domain" "siem" {
  domain_name    = "${var.cluster_name}-os"
  engine_version = "OpenSearch_2.11"

  cluster_config {
    instance_type  = var.os_instance_type
    instance_count = var.os_instance_count
  }

  ebs_options {
    ebs_enabled = true
    volume_size = var.os_volume_size
    volume_type = "gp3"
  }

  vpc_options {
    subnet_ids         = slice(module.vpc.private_subnets, 0, 1)
    security_group_ids = [aws_security_group.data_plane.id]
  }

  encrypt_at_rest {
    enabled = true
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }
}

output "rds_endpoint" {
  value = aws_db_instance.rds_pgvector.endpoint
}

output "opensearch_endpoint" {
  value = aws_opensearch_domain.siem.endpoint
}
