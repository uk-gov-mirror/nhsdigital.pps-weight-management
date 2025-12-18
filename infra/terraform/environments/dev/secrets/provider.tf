terraform {
  backend "s3" {
    bucket       = "nhse-pps-htsh-terraform-state-bucket"
    key          = "dev/secrets.tfstate"
    region       = "eu-west-2"
    use_lockfile = true
  }
}
provider "aws" {
  region = "eu-west-2"
}