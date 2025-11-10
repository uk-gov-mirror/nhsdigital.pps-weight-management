<# 
.SYNOPSIS
  Scan AWS for resources that match a name prefix and/or Project tag prefix.
  Lists matches across common services; optionally deletes them.

.EXAMPLE
  .\list_resources.ps1 -Prefix "nhse-pps-wm-poc-pr-48-" -Regions "eu-west-2","us-east-1"

.EXAMPLE (with deletions)
  .\list_resources.ps1 -Prefix "nhse-pps-wm-poc-pr-48-" -Delete

.NOTES
  Requires AWS CLI v2 in PATH and valid AWS credentials.
#>

param(
  [Parameter(Mandatory=$true)]
  [string]$Prefix,

  # If not supplied, defaults to same as -Prefix
  [string]$ProjectTagPrefix = $null,

  # Regions to scan (CLOUDFRONT/WAF global bits are handled automatically)
  [string[]]$Regions = @("eu-west-2","us-east-1"),

  # Set to perform deletions (otherwise list-only)
  [switch]$Delete
)

if (-not $ProjectTagPrefix) { $ProjectTagPrefix = $Prefix }

Write-Host "== Sweep start ==" -ForegroundColor Cyan
Write-Host "Prefix: '$Prefix'   ProjectTagPrefix: '$ProjectTagPrefix'   Regions: $($Regions -join ', ')   Delete: $Delete" -ForegroundColor DarkCyan

# Helpers
function Test-HasProjectTagPrefix {
  param([array]$Tags,[string]$Pfx)
  if (-not $Tags) { return $false }
  foreach ($t in $Tags) {
    if ($t.Key -eq "Project" -and $t.Value -like "$Pfx*") { return $true }
  }
  return $false
}

$Found = 0

# =========================
# Tagging API (broad, taggable resources)
# =========================
foreach ($ScanRegion in $Regions) {
  Write-Host "`n-- Tagging API in $ScanRegion (Project starts-with '$ProjectTagPrefix*') --" -ForegroundColor Yellow
  try {
    $json = aws resourcegroupstaggingapi get-resources --region $ScanRegion --tag-filters Key=Project,Values="$ProjectTagPrefix*" --output json | ConvertFrom-Json
    $arns = @($json.ResourceTagMappingList | ForEach-Object { $_.ResourceARN })
    if ($arns.Count -gt 0) {
      $Found += $arns.Count
      $arns | ForEach-Object { [pscustomobject]@{ Region=$ScanRegion; ARN=$_; Service=($_ -split ":")[2] } } |
        Sort-Object Service |
        Format-Table -AutoSize
    } else {
      Write-Host "None found." -ForegroundColor DarkGray
    }
  } catch { Write-Host "Tagging API error ($ScanRegion): $($_.Exception.Message)" -ForegroundColor Red }
}

# =========================
# WAFv2 Web ACLs (CLOUDFRONT/global us-east-1)
# =========================
Write-Host "`n-- WAFv2 CLOUDFRONT (us-east-1) --" -ForegroundColor Yellow
try {
  $cf = aws wafv2 list-web-acls --scope CLOUDFRONT --region us-east-1 | ConvertFrom-Json
  $hits = @($cf.WebACLs | Where-Object { $_.Name -like "$Prefix*" -or $_.Name -like "$ProjectTagPrefix*" })
  if ($hits.Count -gt 0) {
    $Found += $hits.Count
    $hits | Select-Object Name, Id, ARN | Format-Table -AutoSize
    if ($Delete) {
      foreach ($acl in $hits) {
        try {
          $res = aws wafv2 list-resources-for-web-acl --web-acl-arn $acl.ARN --region us-east-1 | ConvertFrom-Json
          foreach ($arn in @($res.ResourceArns)) {
            Write-Host "Disassociating $($acl.Name) from $arn" -ForegroundColor DarkYellow
            aws wafv2 disassociate-web-acl --resource-arn $arn --region us-east-1 | Out-Null
          }
          $lock = aws wafv2 get-web-acl --scope CLOUDFRONT --region us-east-1 --id $acl.Id --name $acl.Name --query LockToken --output text
          Write-Host "Deleting WebACL $($acl.Name)" -ForegroundColor Red
          aws wafv2 delete-web-acl --scope CLOUDFRONT --region us-east-1 --id $acl.Id --name $acl.Name --lock-token $lock | Out-Null
        } catch { Write-Host "WAF CLOUDFRONT delete error: $($_.Exception.Message)" -ForegroundColor Red }
      }
    }
  } else {
    Write-Host "None found." -ForegroundColor DarkGray
  }
} catch { Write-Host "WAF CLOUDFRONT error: $($_.Exception.Message)" -ForegroundColor Red }

# =========================
# WAFv2 Web ACLs (REGIONAL)
# =========================
foreach ($ScanRegion in $Regions) {
  # Only meaningful in workload regions; skip us-east-1 if you want
  if ($ScanRegion -eq "us-east-1") { continue }
  Write-Host "`n-- WAFv2 REGIONAL ($ScanRegion) --" -ForegroundColor Yellow
  try {
    $reg = aws wafv2 list-web-acls --scope REGIONAL --region $ScanRegion | ConvertFrom-Json
    $hits = @($reg.WebACLs | Where-Object { $_.Name -like "$Prefix*" -or $_.Name -like "$ProjectTagPrefix*" })
    if ($hits.Count -gt 0) {
      $Found += $hits.Count
      $hits | Select-Object Name, Id, ARN | Format-Table -AutoSize
      if ($Delete) {
        foreach ($acl in $hits) {
          try {
            $res = aws wafv2 list-resources-for-web-acl --web-acl-arn $acl.ARN --region $ScanRegion | ConvertFrom-Json
            foreach ($arn in @($res.ResourceArns)) {
              Write-Host "Disassociating $($acl.Name) from $arn" -ForegroundColor DarkYellow
              aws wafv2 disassociate-web-acl --resource-arn $arn --region $ScanRegion | Out-Null
            }
            $lock = aws wafv2 get-web-acl --scope REGIONAL --region $ScanRegion --id $acl.Id --name $acl.Name --query LockToken --output text
            Write-Host "Deleting WebACL $($acl.Name)" -ForegroundColor Red
            aws wafv2 delete-web-acl --scope REGIONAL --region $ScanRegion --id $acl.Id --name $acl.Name --lock-token $lock | Out-Null
          } catch { Write-Host "WAF REGIONAL delete error: $($_.Exception.Message)" -ForegroundColor Red }
        }
      }
    } else {
      Write-Host "None found." -ForegroundColor DarkGray
    }
  } catch { Write-Host "WAF REGIONAL error ($ScanRegion): $($_.Exception.Message)" -ForegroundColor Red }
}

# =========================
# EventBridge Scheduler
# =========================
Write-Host "`n-- EventBridge Scheduler --" -ForegroundColor Yellow
foreach ($ScanRegion in $Regions) {
  try {
    $sched = aws scheduler list-schedules --region $ScanRegion --name-prefix $Prefix | ConvertFrom-Json
    $items = @($sched.Schedules)
    if ($items.Count -gt 0) {
      $Found += $items.Count
      $items | Select-Object @{N="Region";E={$ScanRegion}}, Name, GroupName, State | Format-Table -AutoSize
      if ($Delete) {
        foreach ($s in $items) {
          $group = if ($s.GroupName) { $s.GroupName } else { "default" }
          Write-Host "Deleting schedule $($s.Name) (group $group) in $ScanRegion" -ForegroundColor Red
          aws scheduler delete-schedule --region $ScanRegion --name $s.Name --group-name $group | Out-Null
        }
      }
    } else {
      Write-Host "None found in $ScanRegion." -ForegroundColor DarkGray
    }
  } catch { Write-Host "Scheduler error ($ScanRegion): $($_.Exception.Message)" -ForegroundColor Red }
}

# =========================
# CloudFront Distributions (global)
# =========================
Write-Host "`n-- CloudFront distributions (global) --" -ForegroundColor Yellow
try {
  $dist = aws cloudfront list-distributions | ConvertFrom-Json
  $hits = @($dist.DistributionList.Items | Where-Object {
    ($_.Id -like "*$Prefix*") -or ($_.Comment -like "*$Prefix*") -or ($_.Aliases.Items -and ($_.Aliases.Items -join "," -like "*$Prefix*"))
  })
  if ($hits.Count -gt 0) {
    $Found += $hits.Count
    $hits | Select-Object Id, DomainName, Comment | Format-Table -AutoSize
    if ($Delete) {
      Write-Host "(Not auto-deleting CloudFront: requires disable + wait + delete. Say if you want this added.)" -ForegroundColor DarkYellow
    }
  } else {
    Write-Host "None found." -ForegroundColor DarkGray
  }
} catch { Write-Host "CloudFront error: $($_.Exception.Message)" -ForegroundColor Red }

# =========================
# S3 Buckets (global names)
# =========================
Write-Host "`n-- S3 buckets (name starts-with) --" -ForegroundColor Yellow
try {
  $buckets = aws s3api list-buckets | ConvertFrom-Json
  $bhits = @($buckets.Buckets | Where-Object { $_.Name -like "$Prefix*" })
  if ($bhits.Count -gt 0) {
    $Found += $bhits.Count
    $bhits | Select-Object Name | Format-Table -AutoSize
    if ($Delete) {
      Write-Host "(Not auto-deleting S3 buckets: destructive; can add force-empty if you want.)" -ForegroundColor DarkYellow
    }
  } else {
    Write-Host "None found." -ForegroundColor DarkGray
  }
} catch { Write-Host "S3 list error: $($_.Exception.Message)" -ForegroundColor Red }

# =========================
# ECR Repositories
# =========================
Write-Host "`n-- ECR repositories --" -ForegroundColor Yellow
foreach ($ScanRegion in $Regions) {
  try {
    $repos = aws ecr describe-repositories --region $ScanRegion | ConvertFrom-Json
    $rhits = @($repos.repositories | Where-Object { $_.repositoryName -like "$Prefix*" })
    if ($rhits.Count -gt 0) {
      $Found += $rhits.Count
      $rhits | Select-Object @{N="Region";E={$ScanRegion}}, repositoryName | Format-Table -AutoSize
      if ($Delete) {
        foreach ($repo in $rhits) {
          Write-Host "Force deleting ECR repo $($repo.repositoryName) in $ScanRegion" -ForegroundColor Red
          aws ecr delete-repository --region $ScanRegion --repository-name $repo.repositoryName --force | Out-Null
        }
      }
    } else {
      Write-Host "None found in $ScanRegion." -ForegroundColor DarkGray
    }
  } catch { Write-Host "ECR error ($ScanRegion): $($_.Exception.Message)" -ForegroundColor Red }
}

# =========================
# ALBs & Target Groups
# =========================
Write-Host "`n-- ALBs & Target Groups --" -ForegroundColor Yellow
foreach ($ScanRegion in $Regions) {
  try {
    $lbs = aws elbv2 describe-load-balancers --region $ScanRegion | ConvertFrom-Json
    $lbHits = @($lbs.LoadBalancers | Where-Object { $_.LoadBalancerName -like "$Prefix*" })
    if ($lbHits.Count -gt 0) {
      $Found += $lbHits.Count
      $lbHits | Select-Object @{N="Region";E={$ScanRegion}}, LoadBalancerName, LoadBalancerArn, Type, Scheme | Format-Table -AutoSize
      if ($Delete) {
        foreach ($lb in $lbHits) {
          Write-Host "Deleting ALB $($lb.LoadBalancerName) in $ScanRegion" -ForegroundColor Red
          aws elbv2 delete-load-balancer --region $ScanRegion --load-balancer-arn $lb.LoadBalancerArn | Out-Null
        }
      }
    } else {
      Write-Host "No ALBs in $ScanRegion." -ForegroundColor DarkGray
    }

    $tgs = aws elbv2 describe-target-groups --region $ScanRegion | ConvertFrom-Json
    $tgHits = @($tgs.TargetGroups | Where-Object { $_.TargetGroupName -like "$Prefix*" })
    if ($tgHits.Count -gt 0) {
      $Found += $tgHits.Count
      $tgHits | Select-Object @{N="Region";E={$ScanRegion}}, TargetGroupName, TargetGroupArn | Format-Table -AutoSize
      if ($Delete) {
        foreach ($tg in $tgHits) {
          Write-Host "Deleting Target Group $($tg.TargetGroupName) in $ScanRegion" -ForegroundColor Red
          aws elbv2 delete-target-group --region $ScanRegion --target-group-arn $tg.TargetGroupArn | Out-Null
        }
      }
    } else {
      Write-Host "No Target Groups in $ScanRegion." -ForegroundColor DarkGray
    }
  } catch { Write-Host "ELBv2 error ($ScanRegion): $($_.Exception.Message)" -ForegroundColor Red }
}

# =========================
# CloudWatch Log Groups
# =========================
Write-Host "`n-- CloudWatch Log Groups --" -ForegroundColor Yellow
foreach ($ScanRegion in $Regions) {
  try {
    $logs = aws logs describe-log-groups --region $ScanRegion | ConvertFrom-Json
    $lghits = @($logs.logGroups | Where-Object { $_.logGroupName -like "*$Prefix*" })
    if ($lghits.Count -gt 0) {
      $Found += $lghits.Count
      $lghits | Select-Object @{N="Region";E={$ScanRegion}}, logGroupName | Format-Table -AutoSize
      if ($Delete) {
        foreach ($lg in $lghits) {
          Write-Host "Deleting log group $($lg.logGroupName) in $ScanRegion" -ForegroundColor Red
          aws logs delete-log-group --region $ScanRegion --log-group-name $lg.logGroupName | Out-Null
        }
      }
    } else {
      Write-Host "None found in $ScanRegion." -ForegroundColor DarkGray
    }
  } catch { Write-Host "CloudWatch Logs error ($ScanRegion): $($_.Exception.Message)" -ForegroundColor Red }
}

# =========================
# EC2 Networking by Name tag or Project tag (VPC/Subnets/NAT/IGW/EIPs)
# =========================
foreach ($ScanRegion in $Regions) {
  if ($ScanRegion -eq "us-east-1") { continue } # usually not used for your VPCs
  Write-Host "`n-- EC2 Networking ($ScanRegion) --" -ForegroundColor Yellow
  try {
    # VPCs
    $vpcl = aws ec2 describe-vpcs --region $ScanRegion | ConvertFrom-Json
    $vpch = @($vpcl.Vpcs | Where-Object { Test-HasProjectTagPrefix $_.Tags $ProjectTagPrefix -or (($_.Tags | Where-Object Key -eq "Name").Value -like "$Prefix*") })
    $vpch | Select-Object VpcId, @{N="Name";E={($_.Tags | Where-Object Key -eq "Name").Value}} | Format-Table -AutoSize
    $Found += $vpch.Count

    # Subnets
    $snet = aws ec2 describe-subnets --region $ScanRegion | ConvertFrom-Json
    $snh  = @($snet.Subnets | Where-Object { Test-HasProjectTagPrefix $_.Tags $ProjectTagPrefix -or (($_.Tags | Where-Object Key -eq "Name").Value -like "$Prefix*") })
    $snh | Select-Object SubnetId, VpcId, @{N="Name";E={($_.Tags | Where-Object Key -eq "Name").Value}} | Format-Table -AutoSize
    $Found += $snh.Count

    # NAT gateways
    $ngw = aws ec2 describe-nat-gateways --region $ScanRegion | ConvertFrom-Json
    $ngh = @($ngw.NatGateways | Where-Object { Test-HasProjectTagPrefix $_.Tags $ProjectTagPrefix -or (($_.Tags | Where-Object Key -eq "Name").Value -like "$Prefix*") })
    $ngh | Select-Object NatGatewayId, State | Format-Table -AutoSize
    $Found += $ngh.Count
    if ($Delete) {
      foreach ($n in $ngh) {
        Write-Host "Deleting NAT GW $($n.NatGatewayId) in $ScanRegion" -ForegroundColor Red
        aws ec2 delete-nat-gateway --region $ScanRegion --nat-gateway-id $n.NatGatewayId | Out-Null
      }
    }

    # Internet gateways
    $igw = aws ec2 describe-internet-gateways --region $ScanRegion | ConvertFrom-Json
    $igh = @($igw.InternetGateways | Where-Object { Test-HasProjectTagPrefix $_.Tags $ProjectTagPrefix -or (($_.Tags | Where-Object Key -eq "Name").Value -like "$Prefix*") })
    $igh | Select-Object InternetGatewayId | Format-Table -AutoSize
    $Found += $igh.Count
    if ($Delete) {
      foreach ($g in $igh) {
        foreach ($att in @($g.Attachments)) {
          Write-Host "Detaching IGW $($g.InternetGatewayId) from VPC $($att.VpcId)" -ForegroundColor DarkYellow
          aws ec2 detach-internet-gateway --region $ScanRegion --internet-gateway-id $g.InternetGatewayId --vpc-id $att.VpcId | Out-Null
        }
        Write-Host "Deleting IGW $($g.InternetGatewayId)" -ForegroundColor Red
        aws ec2 delete-internet-gateway --region $ScanRegion --internet-gateway-id $g.InternetGatewayId | Out-Null
      }
    }

    # Elastic IPs
    $eips = aws ec2 describe-addresses --region $ScanRegion | ConvertFrom-Json
    $eih  = @($eips.Addresses | Where-Object { Test-HasProjectTagPrefix $_.Tags $ProjectTagPrefix })
    $eih | Select-Object AllocationId, PublicIp | Format-Table -AutoSize
    $Found += $eih.Count
    if ($Delete) {
      foreach ($e in $eih) {
        Write-Host "Releasing EIP $($e.AllocationId) ($($e.PublicIp))" -ForegroundColor Red
        aws ec2 release-address --region $ScanRegion --allocation-id $e.AllocationId | Out-Null
      }
    }
  } catch { Write-Host "EC2 networking error ($ScanRegion): $($_.Exception.Message)" -ForegroundColor Red }
}

Write-Host "`n== Sweep complete =="$ -ForegroundColor Cyan
if ($Found -gt 0) {
  Write-Host "Found $Found matching items across services. Review output above." -ForegroundColor Green
} else {
  Write-Host "No resources matched the prefix or Project tag prefix." -ForegroundColor DarkGray
}
