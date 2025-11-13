# Set security groups and then try and make the DB connection if the connection hangs

$rdsEndpoint = terraform output -raw rds_endpoint
$bastionId = terraform output -raw bastion_instance_id

$sgBastion = aws ec2 describe-instances `
  --instance-ids $bastionId `
  --query "Reservations[0].Instances[0].SecurityGroups[0].GroupId" `
  --output text

$rds = aws rds describe-db-instances `
  --query "DBInstances[?Endpoint.Address=='$rdsEndpoint']|[0]" `
  --output json | ConvertFrom-Json

$rdsSgIds = $rds.VpcSecurityGroups | ForEach-Object { $_.VpcSecurityGroupId }

foreach ($sg in $rdsSgIds) {
  Write-Host "---- $sg ----"
  aws ec2 describe-security-groups --group-ids $sg `
    --query "SecurityGroups[0].IpPermissions[]" `
    --output table
}

foreach ($sg in $rdsSgIds) {
  aws ec2 authorize-security-group-ingress `
    --group-id $sg `
    --protocol tcp `
    --port 5432 `
    --source-group $sgBastion 2>$null
}

foreach ($sg in $rdsSgIds) {
  Write-Host "---- $sg ----"
  aws ec2 describe-security-groups --group-ids $sg `
    --query "SecurityGroups[0].IpPermissions[]" `
    --output table
}

$env:PGPASSWORD = $dbPass
psql "host=127.0.0.1 port=5432 dbname=$dbName user=$dbUser sslmode=require"
