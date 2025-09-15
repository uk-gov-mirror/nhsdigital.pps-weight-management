####################################################################
#
# Terraform State Backup
# ----------------------
# 
# - Terraform state is stored in the S3 instance created in this script
# 
# Create backend resources (run once)
#
# > cd infra/terraform/bootstrap
# > terraform init
# > terraform apply -auto-approve
# 
####################################################################

# S3 bucket for storing the Terraform state file.
# This centralizes the state and allows multiple users
# to work on the same infrastructure without conflicts.
resource "aws_s3_bucket" "terraform_state" {
  bucket = "nhse-pps-wm-terraform-state-bucket"

  # Enable versioning to keep a history of the state files,
  # which is crucial for disaster recovery and undoing bad changes.
  versioning {
    enabled = true
  }

  # Enforce server-side encryption for all objects in the bucket
  # to secure the state file at rest.
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  # Add a tag to easily identify the bucket's purpose.
  tags = {
    Name    = "Terraform State Bucket"
	Project = "nhse-pps-wm"
  }
}

# DynamoDB table for state locking.
# This prevents multiple users from running `terraform apply` at the same time,
# which could corrupt the state file.
resource "aws_dynamodb_table" "terraform_locks" {
  name         = "nhse-pps-wm-terraform-state-lock-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  # Define the primary key for the lock table.
  attribute {
    name = "LockID"
    type = "S"
  }

  # Add a tag to easily identify the table's purpose.
  tags = {
    Name    = "Terraform State Lock Table"
	Project = "nhse-pps-wm"
  }
}
