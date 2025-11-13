# Needs the SessionManagerPlugin to be installed: https://docs.aws.amazon.com/systems-manager/latest/userguide/install-plugin-windows.html

# Open 1st PowerShell Window

# Run in the terraform folder
cd .\infra\terraform

# Set WM env to connect to
$wm_env = 'pr-50'

# Sign in to aws
$env:AWS_PROFILE = 'admin-pps-wm'
$env:AWS_REGION  = 'eu-west-2'
$env:AWS_SDK_LOAD_CONFIG = '1'

aws sso login --profile admin-pps-wm

# Init terraform
terraform init -reconfigure  `
               -backend-config="bucket=nhse-pps-wm-terraform-state-bucket"  `
			   -backend-config="region=eu-west-2"  `
			   -backend-config="dynamodb_table=nhse-pps-wm-terraform-state-lock-table"  `
			   -backend-config="key=$wm_env/terraform.tfstate" 

# Get the bastion EC2 instance ID
$bastionId   = terraform output -raw bastion_instance_id

# Get the RDS endpoint hostname
$rdsEndpoint = terraform output -raw rds_endpoint


@ Start the AWS port forward
$param = @{ host = @($rdsEndpoint); portNumber = @("5432"); localPortNumber = @("5432") } | ConvertTo-Json -Compress
aws ssm start-session `
  --target $bastionId `
  --document-name AWS-StartPortForwardingSessionToRemoteHost `
  --parameters $param

# Open 2nd PowerShell Window

# Run in the terraform folder
cd .\infra\terraform

# Sign in to aws
$env:AWS_PROFILE = 'admin-pps-wm'
$env:AWS_REGION  = 'eu-west-2'
$env:AWS_SDK_LOAD_CONFIG = '1'

aws sso login --profile admin-pps-wm

# Get the SSM parameter name that stores the DB password
$ssmParam    = terraform output -raw ssm_db_password_param

# Load the DB password securely from SSM
$dbPass = aws ssm get-parameter `
  --name $ssmParam `
  --with-decryption `
  --query 'Parameter.Value' `
  --output text

# Load DB info
$dbName = "appdb"
$dbUser = "appuser"

$env:PGPASSWORD = $dbPass
psql "host=127.0.0.1 port=5432 dbname=$dbName user=$dbUser sslmode=require"

# If the connection hangs try the alternate script that sets the security groups

# Sample queries
\dt
SELECT COUNT(*) FROM "V1_SERVICE";
SELECT * FROM "V1_SERVICE" LIMIT 5;