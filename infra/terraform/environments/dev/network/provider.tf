terraform {
  backend "s3" {
    bucket       = "nhse-pps-htsh-terraform-state-bucket"
    key          = "dev/network.tfstate"
    region       = "eu-west-2"
    use_lockfile = true
  }
}

provider "aws" {
  region = "eu-west-2"
}
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}