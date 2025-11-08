# Destroy all AWS resources for an environment identified by Project tag

# Usage:

# Dry run
# .\destroy_environment.ps1 -Env {poc} -Profile {aws_profile} -WhatIf

# Actually delete
# .\destroy_environment.ps1 -Env {poc} -Profile {aws_profile}

# Wait on long operations
# .\destroy_environment.ps1 -Env {poc} -Profile {aws_profile} -Wait

# Skip RDS snapshots
# .\destroy_environment.ps1 -Env {poc} -Profile {aws_profile} -SkipFinalSnapshots -Wait

param(
  [Parameter(Mandatory=$true)]
  [string]$Env,
  [string]$Region = "eu-west-2",
  [string]$Profile = $null,
  [switch]$WhatIf,
  [switch]$SkipFinalSnapshots,
  [switch]$Wait
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectValue = "nhse-pps-wm-$Env"

$commonArgs = @("--region", $Region)
if ($Profile) { $commonArgs += @("--profile", $Profile) }

$profileDisplay = if ($Profile) { $Profile } else { 'default env' }
Write-Host "Region: $Region | Project: $ProjectValue | Profile: $profileDisplay"
if ($WhatIf) { Write-Host "** DRY RUN (no deletions). Use -WhatIf:`$false to actually delete. **" -ForegroundColor Yellow }

# ------------------ Helpers ------------------

function ConvertTo-TagPairs {
  param($Raw)
  $pairs = @()
  if ($null -eq $Raw) { return $pairs }

  if ($Raw -is [System.Collections.IDictionary]) {
    foreach ($k in $Raw.Keys) { $pairs += @{ Key = $k; Value = $Raw[$k] } }
    return $pairs
  }
  if ($Raw -is [System.Management.Automation.PSCustomObject]) {
    foreach ($p in $Raw.PSObject.Properties) { $pairs += @{ Key = $p.Name; Value = $p.Value } }
    return $pairs
  }
  if ($Raw -is [System.Collections.IEnumerable] -and -not ($Raw -is [string])) {
    foreach ($item in $Raw) {
      if ($null -eq $item) { continue }
      if ($item.PSObject.Properties.Match('Key').Count -gt 0 -and $item.PSObject.Properties.Match('Value').Count -gt 0) {
        $pairs += @{ Key = $item.Key; Value = $item.Value }
      } elseif ($item -is [System.Collections.IDictionary]) {
        foreach ($k in $item.Keys) { $pairs += @{ Key = $k; Value = $item[$k] } }
      } elseif ($item -is [System.Management.Automation.PSCustomObject]) {
        foreach ($p in $item.PSObject.Properties) { $pairs += @{ Key = $p.Name; Value = $p.Value } }
      }
    }
  }
  return $pairs
}

function Has-TagKV {
  param($Tags, [string]$Key, [string]$Val)
  foreach ($t in (ConvertTo-TagPairs $Tags)) {
    if ($t.Key -eq $Key -and "$($t.Value)" -eq "$Val") { return $true }
  }
  return $false
}

function Ensure-AwsAuth {
  param([string]$ProfileToUse)
  if (-not $ProfileToUse) { return $true }
  $out = & aws sts get-caller-identity @("--region",$Region) @("--profile",$ProfileToUse) 2>&1
  if ($LASTEXITCODE -eq 0) { return $true }
  $text = ($out | Out-String)
  if ($text -match "Token has expired" -or $text -match "SSO" -or $text -match "The SSO session associated") {
    Write-Host "SSO token expired. Running: aws sso login --profile $ProfileToUse" -ForegroundColor Yellow
    & aws sso login @("--profile",$ProfileToUse)
    if ($LASTEXITCODE -ne 0) { Write-Error "aws sso login failed. Please run it manually and re-run the script."; return $false }
    & aws sts get-caller-identity @("--region",$Region) @("--profile",$ProfileToUse) | Out-Null
    return ($LASTEXITCODE -eq 0)
  }
  Write-Warning "AWS auth check failed: $text"
  return $false
}

function Invoke-Aws {
  param([object[]]$ArgList)
  if (-not $ArgList -or $ArgList.Count -eq 0) { return "" }
  $op = ($ArgList.Count -ge 2) ? [string]$ArgList[1] : ""
  $isRead = $op -match '^(describe|get|list|wait)$'
  $exe = "aws"
  $all = @($ArgList) + $commonArgs
  $flat = New-Object System.Collections.Generic.List[string]
  foreach ($a in $all) {
    if ($null -eq $a) { continue }
    if ($a -is [System.Collections.IEnumerable] -and -not ($a -is [string])) { foreach ($x in $a) { if ($null -ne $x) { [void]$flat.Add([string]$x) } } }
    else { [void]$flat.Add([string]$a) }
  }
  Write-Host ">> $exe $($flat -join ' ')"
  if ($WhatIf -and -not $isRead) { return "" }
  for ($attempt=1; $attempt -le 2; $attempt++) {
    $out = & $exe @flat 2>&1
    $code = $LASTEXITCODE
    if ($code -eq 0) { return ($out -join "`n") }
    $text = ($out | Out-String)
    if ($attempt -eq 1 -and ($text -match "Token has expired" -or $text -match "The SSO session associated")) {
      if ($Profile) {
        Write-Host "Detected expired SSO token. Running aws sso login --profile $Profile and retrying..." -ForegroundColor Yellow
        & aws sso login @("--profile",$Profile); if ($LASTEXITCODE -ne 0) { Write-Warning "aws sso login failed."; break }
        continue
      }
    }
    Write-Warning ("AWS CLI exited with {0}: {1}" -f $code, ($text.Trim()))
    break
  }
  return ""
}

# ---------- Preflight ----------
if ($Profile) {
  if (-not (Ensure-AwsAuth -ProfileToUse $Profile)) {
    Write-Warning "AWS auth preflight failed, but continuing so you can see step output…"
  }
}
$who = Invoke-Aws @("sts","get-caller-identity")
if (-not $who) {
  Write-Warning "Could not get caller identity via helper. Trying a direct CLI call (bypassing wrapper)…"
  $who = (& aws sts get-caller-identity @("--region",$Region) @("--profile",$Profile) 2>&1) -join "`n"
}
if ($who) {
  try {
    $whoObj = $who | ConvertFrom-Json
    $AccountId = $whoObj.Account
    Write-Host ("Authenticated to Account: {0} | User/Role: {1}" -f $AccountId, $whoObj.Arn) -ForegroundColor Cyan
  } catch {
    Write-Warning "Preflight returned non-JSON output:`n$who"
  }
} else {
  Write-Warning "Still couldn't read caller identity. Proceeding anyway so steps print their own errors."
}

# ------------------ Resource deletion functions ------------------

function Remove-EC2Instances {
  $json = Invoke-Aws @("ec2","describe-instances","--filters","Name=tag:Project,Values=$ProjectValue")
  if (-not $json) { return }
  $data = $json | ConvertFrom-Json
  $ids = @()
  foreach ($res in ($data.Reservations | Where-Object { $_.Instances })) {
    foreach ($i in $res.Instances) {
      if ($i.State.Name -in @("shutting-down","terminated")) { continue }
      $ids += $i.InstanceId
    }
  }
  if ($ids.Count -gt 0) {
    Write-Host "EC2 terminate: $($ids -join ', ')"
    if (-not $WhatIf) {
      [void](Invoke-Aws (@("ec2","terminate-instances","--instance-ids") + $ids))
      if ($Wait) { [void](Invoke-Aws (@("ec2","wait","instance-terminated","--instance-ids") + $ids)) }
    }
  } else {
    Write-Host "No EC2 instances with Project=$ProjectValue"
  }
}

function Remove-ASG {
  $json = Invoke-Aws @("autoscaling","describe-auto-scaling-groups")
  if (-not $json) { return }
  $data = $json | ConvertFrom-Json
  $found = $false
  foreach ($g in $data.AutoScalingGroups) {
    if (-not (Has-TagKV $g.Tags "Project" $ProjectValue)) { continue }
    $found = $true
    Write-Host "ASG delete: $($g.AutoScalingGroupName)"
    if (-not $WhatIf) {
      [void](Invoke-Aws @("autoscaling","update-auto-scaling-group","--auto-scaling-group-name",$g.AutoScalingGroupName,"--min-size","0","--max-size","0","--desired-capacity","0"))
      [void](Invoke-Aws @("autoscaling","delete-auto-scaling-group","--auto-scaling-group-name",$g.AutoScalingGroupName,"--force-delete"))
    }
  }
  if (-not $found) { Write-Host "No ASGs with Project=$ProjectValue" }
}

function Remove-ECS {
  $next = $null
  $clusterArns = @()
  do {
    $args = @("ecs","list-clusters")
    if ($next) { $args += @("--next-token",$next) }
    $json = Invoke-Aws $args
    if (-not $json) { break }
    $obj = $json | ConvertFrom-Json
    if ($obj.clusterArns) { $clusterArns += $obj.clusterArns }
    $next = if ($obj.PSObject.Properties.Match('nextToken').Count -gt 0) { $obj.nextToken } else { $null }
  } while ($next)

  if (-not $clusterArns -or $clusterArns.Count -eq 0) { Write-Host "No ECS clusters found"; return }

  $matched = $false
  foreach ($arn in $clusterArns) {
    if (-not $arn) { continue }
    $tagPairsInput = @{}
    $tagJson = Invoke-Aws @("ecs","list-tags-for-resource","--resource-arn",$arn)
    if ($tagJson) {
      $tagObj = $tagJson | ConvertFrom-Json
      $tagPairsInput = $tagObj.tags
    } else {
      $descJson = Invoke-Aws @("ecs","describe-clusters","--clusters",$arn,"--include","TAGS")
      if ($descJson) {
        $cl = ($descJson | ConvertFrom-Json).clusters[0]
        $tagPairsInput = $cl.tags
      }
    }
    if (-not (Has-TagKV $tagPairsInput "Project" $ProjectValue)) { continue }
    $matched = $true

    # services (paginated)
    $svcNext = $null; $services = @()
    do {
      $sargs = @("ecs","list-services","--cluster",$arn)
      if ($svcNext) { $sargs += @("--next-token",$svcNext) }
      $sjson = Invoke-Aws $sargs
      if (-not $sjson) { break }
      $sobj = $sjson | ConvertFrom-Json
      if ($sobj.serviceArns) { $services += $sobj.serviceArns }
      $svcNext = if ($sobj.PSObject.Properties.Match('nextToken').Count -gt 0) { $sobj.nextToken } else { $null }
    } while ($svcNext)

    foreach ($svc in $services) {
      Write-Host "ECS service delete: $svc"
      if (-not $WhatIf) {
        [void](Invoke-Aws @("ecs","update-service","--cluster",$arn,"--service",$svc,"--desired-count","0"))
        [void](Invoke-Aws @("ecs","delete-service","--cluster",$arn,"--service",$svc,"--force"))
      }
    }

    # running tasks (paginated)
    $taskNext = $null; $tasks = @()
    do {
      $targs = @("ecs","list-tasks","--cluster",$arn)
      if ($taskNext) { $targs += @("--next-token",$taskNext) }
      $tjson = Invoke-Aws $targs
      if (-not $tjson) { break }
      $tobj = $tjson | ConvertFrom-Json
      if ($tobj.taskArns) { $tasks += $tobj.taskArns }
      $taskNext = if ($tobj.PSObject.Properties.Match('nextToken').Count -gt 0) { $tobj.nextToken } else { $null }
    } while ($taskNext)

    foreach ($t in $tasks) {
      Write-Host "ECS task stop: $t"
      if (-not $WhatIf) { [void](Invoke-Aws @("ecs","stop-task","--cluster",$arn,"--task",$t,"--reason","cleanup")) }
    }

    Write-Host "ECS cluster delete: $arn"
    if (-not $WhatIf) { [void](Invoke-Aws @("ecs","delete-cluster","--cluster",$arn)) }
  }
  if (-not $matched) { Write-Host "No ECS clusters with Project=$ProjectValue" }
}

function Remove-ECSTaskDefsByTag {
  $toDelete = New-Object System.Collections.Generic.List[string]

  foreach ($status in @("ACTIVE","INACTIVE")) {
    $next = $null
    do {
      $args = @("ecs","list-task-definitions","--status",$status)
      if ($next) { $args += @("--next-token",$next) }
      $j = Invoke-Aws $args
      if (-not $j) { break }
      $o = $null; try { $o = $j | ConvertFrom-Json } catch {}
      if (-not $o) { break }

      $arns = if ($o.PSObject.Properties.Match('taskDefinitionArns').Count -gt 0) { $o.taskDefinitionArns } else { @() }
      foreach ($tdArn in $arns) {
        $tJson = Invoke-Aws @("ecs","list-tags-for-resource","--resource-arn",$tdArn)
        $tags = @{}
        if ($tJson) { try { $tags = ($tJson | ConvertFrom-Json).tags } catch {} }
        if (Has-TagKV $tags "Project" $ProjectValue) { [void]$toDelete.Add($tdArn) }
      }

      $next = if ($o.PSObject.Properties.Match('nextToken').Count -gt 0) { $o.nextToken } else { $null }
    } while ($next)
  }

  if ($toDelete.Count -gt 0) {
    Invoke-EcsDeleteTaskDefs -Arns $toDelete
  } else {
    Write-Host "No ECS task definitions with Project=$ProjectValue"
  }
}

function Remove-ECSTaskDefsAndClusterByName {
  # First: task definitions by family prefix (both ACTIVE/INACTIVE), then cluster/services
  $families = @("nhse-pps-wm-$Env-django","nhse-pps-wm-$Env-cron")
  $toDelete = New-Object System.Collections.Generic.List[string]

  foreach ($f in $families) {
    foreach ($status in @("ACTIVE","INACTIVE")) {
      $next = $null
      do {
        $args = @("ecs","list-task-definitions","--family-prefix",$f,"--status",$status)
        if ($next) { $args += @("--next-token",$next) }
        $j = Invoke-Aws $args
        if (-not $j) { break }
        $o = $null; try { $o = $j | ConvertFrom-Json } catch {}
        if (-not $o) { break }
        $arns = if ($o.PSObject.Properties.Match('taskDefinitionArns').Count -gt 0) { $o.taskDefinitionArns } else { @() }
        foreach ($arn in $arns) { [void]$toDelete.Add($arn) }
        $next = if ($o.PSObject.Properties.Match('nextToken').Count -gt 0) { $o.nextToken } else { $null }
      } while ($next)
    }
  }

  if ($toDelete.Count -gt 0) {
    Invoke-EcsDeleteTaskDefs -Arns $toDelete
  }

  # Then: services/tasks/cluster teardown by name (safe even if already gone)
  $cname = "nhse-pps-wm-$Env-ecs"

  $descJson = Invoke-Aws @("ecs","describe-clusters","--clusters",$cname)
  if ($descJson) {
    $desc = $null; try { $desc = $descJson | ConvertFrom-Json } catch {}
    $cluster = $null
    if ($desc -and $desc.PSObject.Properties.Match('clusters').Count -gt 0 -and $desc.clusters) {
      $cluster = $desc.clusters | Where-Object { $_.clusterName -eq $cname -and $_.status }
    }

    if ($cluster) {
      # services
      $svcNext = $null; $svcs = @()
      do {
        $sargs = @("ecs","list-services","--cluster",$cname)
        if ($svcNext) { $sargs += @("--next-token",$svcNext) }
        $sjson = Invoke-Aws $sargs
        if (-not $sjson) { break }
        $sobj = $null; try { $sobj = $sjson | ConvertFrom-Json } catch {}
        if ($sobj -and $sobj.PSObject.Properties.Match('serviceArns').Count -gt 0 -and $sobj.serviceArns) { $svcs += $sobj.serviceArns }
        $svcNext = if ($sobj -and $sobj.PSObject.Properties.Match('nextToken').Count -gt 0) { $sobj.nextToken } else { $null }
      } while ($svcNext)

      foreach ($s in $svcs) {
        Write-Host "ECS service delete: $s"
        if (-not $WhatIf) {
          [void](Invoke-Aws @("ecs","update-service","--cluster",$cname,"--service",$s,"--desired-count","0"))
          [void](Invoke-Aws @("ecs","delete-service","--cluster",$cname,"--service",$s,"--force"))
        }
      }

      # running tasks
      $taskNext = $null; $tasks = @()
      do {
        $targs = @("ecs","list-tasks","--cluster",$cname)
        if ($taskNext) { $targs += @("--next-token",$taskNext) }
        $tjson = Invoke-Aws $targs
        if (-not $tjson) { break }
        $tobj = $null; try { $tobj = $tjson | ConvertFrom-Json } catch {}
        if ($tobj -and $tobj.PSObject.Properties.Match('taskArns').Count -gt 0 -and $tobj.taskArns) { $tasks += $tobj.taskArns }
        $taskNext = if ($tobj -and $tobj.PSObject.Properties.Match('nextToken').Count -gt 0) { $tobj.nextToken } else { $null }
      } while ($taskNext)

      foreach ($t in $tasks) {
        Write-Host "ECS task stop: $t"
        if (-not $WhatIf) { [void](Invoke-Aws @("ecs","stop-task","--cluster",$cname,"--task",$t,"--reason","cleanup")) }
      }

      Write-Host "ECS cluster delete: $cname"
      if (-not $WhatIf) { [void](Invoke-Aws @("ecs","delete-cluster","--cluster",$cname)) }
    } else {
      Write-Host "ECS cluster not found: $cname"
    }
  } else {
    Write-Host "ECS cluster not found: $cname"
  }
}

function Remove-Lambda {
  $json = Invoke-Aws @("lambda","list-functions")
  if (-not $json) { return }
  $data = $json | ConvertFrom-Json
  $found = $false
  foreach ($f in $data.Functions) {
    $tagsJson = Invoke-Aws @("lambda","list-tags","--resource",$f.FunctionArn)
    $tagsObj  = $null
    if ($tagsJson) { $tagsObj = ($tagsJson | ConvertFrom-Json).Tags }
    if (-not (Has-TagKV $tagsObj "Project" $ProjectValue)) { continue }
    $found = $true
    Write-Host "Lambda delete: $($f.FunctionName)"
    if (-not $WhatIf) { [void](Invoke-Aws @("lambda","delete-function","--function-name",$f.FunctionName)) }
  }
  if (-not $found) { Write-Host "No Lambda functions with Project=$ProjectValue" }
}

function Remove-ELBv2 {
  $json = Invoke-Aws @("elbv2","describe-load-balancers")
  if (-not $json) { return }
  $lbs = ($json | ConvertFrom-Json).LoadBalancers
  $found = $false
  foreach ($lb in $lbs) {
    $tagsJson = Invoke-Aws @("elbv2","describe-tags","--resource-arns",$lb.LoadBalancerArn)
    if (-not $tagsJson) { continue }
    $td = ($tagsJson | ConvertFrom-Json).TagDescriptions[0].Tags
    if (-not (Has-TagKV $td "Project" $ProjectValue)) { continue }
    $found = $true

    $lisJson = Invoke-Aws @("elbv2","describe-listeners","--load-balancer-arn",$lb.LoadBalancerArn)
    if ($lisJson) {
      foreach ($li in (($lisJson | ConvertFrom-Json).Listeners)) {
        Write-Host "ELBv2 listener delete: $($li.ListenerArn)"
        if (-not $WhatIf) { [void](Invoke-Aws @("elbv2","delete-listener","--listener-arn",$li.ListenerArn)) }
      }
    }

    $tgsJson = Invoke-Aws @("elbv2","describe-target-groups","--load-balancer-arn",$lb.LoadBalancerArn)

    Write-Host "ELBv2 delete: $($lb.LoadBalancerName)"
    if (-not $WhatIf) { [void](Invoke-Aws @("elbv2","delete-load-balancer","--load-balancer-arn",$lb.LoadBalancerArn)) }

    if ($tgsJson) {
      foreach ($tg in (($tgsJson | ConvertFrom-Json).TargetGroups)) {
        Write-Host "ELBv2 target-group delete: $($tg.TargetGroupArn)"
        if (-not $WhatIf) { [void](Invoke-Aws @("elbv2","delete-target-group","--target-group-arn",$tg.TargetGroupArn)) }
      }
    }
  }
  if (-not $found) { Write-Host "No ALBs/NLBs with Project=$ProjectValue" }
}

function Remove-OrphanTargetGroups {
  $j = Invoke-Aws @("elbv2","describe-target-groups")
  if (-not $j) { return }
  $found = $false
  $tgs = ($j | ConvertFrom-Json).TargetGroups
  if (-not $tgs) { Write-Host "No target groups found"; return }
  foreach ($tg in $tgs) {
    $tagsJson = Invoke-Aws @("elbv2","describe-tags","--resource-arns",$tg.TargetGroupArn)
    $tagList = @()
    if ($tagsJson) {
      $tagDesc = ($tagsJson | ConvertFrom-Json).TagDescriptions
      if ($tagDesc -and $tagDesc.Count -gt 0 -and $tagDesc[0].Tags) { $tagList = $tagDesc[0].Tags }
    }
    $pairs = ConvertTo-TagPairs $tagList
    $match = $false
    if (Has-TagKV $pairs "Project" $ProjectValue) { $match = $true }
    if (-not $match -and $tg.TargetGroupName -like "*$Env*") { $match = $true }
    if (-not $match) { continue }

    $found = $true
    Write-Host "ELBv2 target-group delete: $($tg.TargetGroupArn)"
    if (-not $WhatIf) { [void](Invoke-Aws @("elbv2","delete-target-group","--target-group-arn",$tg.TargetGroupArn)) }
  }
  if (-not $found) { Write-Host "No orphan Target Groups with Project/Env" }
}

function Remove-ApiGateway {
  $any = $false
  $restJson = Invoke-Aws @("apigateway","get-rest-apis")
  if ($restJson) {
    $rest = ($restJson | ConvertFrom-Json).items
    foreach ($api in $rest) {
      $arn      = "arn:aws:apigateway:${Region}::/restapis/$($api.id)"
      $tagsJson = Invoke-Aws @("apigateway","get-tags","--resource-arn",$arn)
      $pairsObj = @{}
      if ($tagsJson) { $pairsObj = ($tagsJson | ConvertFrom-Json) }
      if (-not (Has-TagKV $pairsObj "Project" $ProjectValue)) { continue }
      $any = $true
      Write-Host "API Gateway v1 delete: $($api.name) ($($api.id))"
      if (-not $WhatIf) { [void](Invoke-Aws @("apigateway","delete-rest-api","--rest-api-id",$api.id)) }
    }
  }
  $v2Json = Invoke-Aws @("apigatewayv2","get-apis")
  if ($v2Json) {
    $v2 = ($v2Json | ConvertFrom-Json).Items
    foreach ($api in $v2) {
      $tagsJson = Invoke-Aws @("apigatewayv2","get-tags","--resource-arn",$api.ApiArn)
      $pairsObj = @{}
      if ($tagsJson) { $pairsObj = ($tagsJson | ConvertFrom-Json).Tags }
      if (-not (Has-TagKV $pairsObj "Project" $ProjectValue)) { continue }
      $any = $true
      Write-Host "API Gateway v2 delete: $($api.Name) ($($api.ApiId))"
      if (-not $WhatIf) { [void](Invoke-Aws @("apigatewayv2","delete-api","--api-id",$api.ApiId)) }
    }
  }
  if (-not $any) { Write-Host "No API Gateway APIs with Project=$ProjectValue" }
}

function Remove-VPCEndpointsAndNAT {
  $epsJson = Invoke-Aws @("ec2","describe-vpc-endpoints","--filters","Name=tag:Project,Values=$ProjectValue")
  $ngwJson = Invoke-Aws @("ec2","describe-nat-gateways","--filter","Name=tag:Project,Values=$ProjectValue")
  $any = $false
  if ($epsJson) {
    foreach ($ep in (($epsJson | ConvertFrom-Json).VpcEndpoints)) {
      $any = $true
      Write-Host "VPC endpoint delete: $($ep.VpcEndpointId)"
      if (-not $WhatIf) { [void](Invoke-Aws @("ec2","delete-vpc-endpoints","--vpc-endpoint-ids",$ep.VpcEndpointId)) }
    }
  }
  if ($ngwJson) {
    foreach ($ng in (($ngwJson | ConvertFrom-Json).NatGateways)) {
      $any = $true
      Write-Host "NAT Gateway delete: $($ng.NatGatewayId)"
      if (-not $WhatIf) { [void](Invoke-Aws @("ec2","delete-nat-gateway","--nat-gateway-id",$ng.NatGatewayId)) }
    }
  }
  if (-not $any) { Write-Host "No VPC endpoints or NAT gateways with Project=$ProjectValue" }
}

function Remove-EIPs {
  $j = Invoke-Aws @("ec2","describe-addresses","--filters","Name=tag:Project,Values=$ProjectValue")
  $addrs = if ($j) { ($j | ConvertFrom-Json).Addresses } else { @() }
  if (-not $addrs -or $addrs.Count -eq 0) { Write-Host "No EIPs with Project=$ProjectValue"; return }

  foreach ($a in $addrs) {
    $pub   = $a.PublicIp
    $alloc = $a.AllocationId
    $assoc = if ($a.PSObject.Properties.Match('AssociationId').Count -gt 0) { $a.AssociationId } else { $null }
    $domain = if ($a.PSObject.Properties.Match('Domain').Count -gt 0) { $a.Domain } else { $null }

    # 1) Try to disassociate (if any)
    if ($assoc) {
      Write-Host "EIP disassociate: $pub ($assoc)"
      if (-not $WhatIf) {
        $raw = Invoke-Aws @("ec2","disassociate-address","--association-id",$assoc)
        if (-not $raw) {
          Write-Warning "Disassociate failed or returned empty output; will check for NAT Gateway bindings."
        }
      }
    } elseif ($domain -eq "standard" -and $pub) {
      Write-Host "EIP disassociate (classic): $pub"
      if (-not $WhatIf) { [void](Invoke-Aws @("ec2","disassociate-address","--public-ip",$pub)) }
    }

    # 2) Attempt to release
    $needNatCheck = $false
    if ($alloc) {
      Write-Host "EIP release: $alloc"
      if (-not $WhatIf) {
        $out = & aws @("ec2","release-address","--allocation-id",$alloc) @("--region",$Region) @(if($Profile){"--profile",$Profile}) 2>&1
        if ($LASTEXITCODE -ne 0) {
          $txt = ($out | Out-String)
          Write-Warning $txt.Trim()
          if ($txt -match "AuthFailure") { $needNatCheck = $true }
        }
      }
    } else {
      Write-Warning "EIP $pub has no AllocationId; skipping release."
    }

    # 3) If AuthFailure, check for NAT GW holding this EIP (only delete if NAT is tagged for this Project)
    if ($needNatCheck -and $alloc) {
      $natJson = Invoke-Aws @("ec2","describe-nat-gateways","--filter","Name=nat-gateway-address.allocation-id,Values=$alloc")
      $nats = @()
      if ($natJson) { try { $nats = ($natJson | ConvertFrom-Json).NatGateways } catch {} }
      foreach ($ng in $nats) {
        $tags = @(); if ($ng.PSObject.Properties.Match('Tags').Count -gt 0) { $tags = $ng.Tags }
        if (-not (Has-TagKV $tags "Project" $ProjectValue)) {
          Write-Host "Found NAT GW $($ng.NatGatewayId) using $alloc but it is not tagged Project=$ProjectValue — skipping destructive action."
          continue
        }
        Write-Host "Deleting NAT Gateway $($ng.NatGatewayId) that holds EIP $alloc (tagged for this Project)."
        if (-not $WhatIf) {
          [void](Invoke-Aws @("ec2","delete-nat-gateway","--nat-gateway-id",$ng.NatGatewayId))
          if ($Wait) { [void](Invoke-Aws @("ec2","wait","nat-gateway-available","--nat-gateway-ids",$ng.NatGatewayId)) } # best-effort; state model varies
          # Now retry release
          Write-Host "Retry EIP release: $alloc"
          [void](Invoke-Aws @("ec2","release-address","--allocation-id",$alloc))
        }
      }

      if (-not $nats -or $nats.Count -eq 0) {
        Write-Warning "AuthFailure persisted, and no NAT GW found using $alloc. This is likely a cross-account ownership or SCP deny."
        if ($AccountId -and $Profile) {
          Write-Host "To diagnose IAM/SCP, run:" -ForegroundColor Yellow
          Write-Host ("aws iam get-user --profile {0} 2>$null | jq -r '.Arn' ; " -f $Profile) -NoNewline
          Write-Host "aws sts get-caller-identity --profile $Profile"
          Write-Host ("aws iam simulate-principal-policy --policy-source-arn <YOUR_ROLE_OR_USER_ARN> --action-names ec2:DisassociateAddress ec2:ReleaseAddress --resource-arns '*' --context-entries ContextKeyName=ec2:AllocationId,ContextKeyValues=$alloc,ContextKeyType=string --profile $Profile") -ForegroundColor DarkYellow
        }
      }
    }
  }
}

function Remove-S3 {
  $listJson = Invoke-Aws @("s3api","list-buckets")
  if (-not $listJson) { return }
  $buckets = ($listJson | ConvertFrom-Json).Buckets
  $found = $false
  foreach ($b in $buckets) {
    try {
      $tagJson = Invoke-Aws @("s3api","get-bucket-tagging","--bucket",$b.Name)
      if (-not $tagJson) { continue }
      $tagset = ($tagJson | ConvertFrom-Json).TagSet
    } catch { continue }
    if (-not (Has-TagKV $tagset "Project" $ProjectValue)) { continue }

    $found = $true
    Write-Host "S3 empty and delete: s3://$($b.Name)"
    if (-not $WhatIf) {
      $isTruncated = $true; $keyMarker = $null; $verMarker = $null
      while ($isTruncated) {
        $cmdArgs = @("s3api","list-object-versions","--bucket",$b.Name)
        if ($keyMarker) { $cmdArgs += @("--key-marker",$keyMarker) }
        if ($verMarker) { $cmdArgs += @("--version-id-marker",$verMarker) }
        $pageJson = Invoke-Aws $cmdArgs
        if (-not $pageJson) { break }
        $page = $pageJson | ConvertFrom-Json
        $versions = @()
        if ($page.Versions) { $versions += $page.Versions }
        if ($page.DeleteMarkers) { $versions += $page.DeleteMarkers }
        foreach ($v in $versions) {
          [void](Invoke-Aws @("s3api","delete-object","--bucket",$b.Name,"--key",$v.Key,"--version-id",$v.VersionId))
        }
        $isTruncated = [bool](if ($page.PSObject.Properties.Match('IsTruncated').Count -gt 0) { $page.IsTruncated } else { $false })
        $keyMarker = if ($page.PSObject.Properties.Match('NextKeyMarker').Count -gt 0) { $page.NextKeyMarker } else { $null }
        $verMarker = if ($page.PSObject.Properties.Match('NextVersionIdMarker').Count -gt 0) { $page.NextVersionIdMarker } else { $null }
      }
      [void](Invoke-Aws @("s3api","delete-bucket","--bucket",$b.Name))
    }
  }
  if (-not $found) { Write-Host "No S3 buckets with Project=$ProjectValue" }
}

function Remove-ECR {
  $reposJson = Invoke-Aws @("ecr","describe-repositories")
  if (-not $reposJson) { return }
  $repos = ($reposJson | ConvertFrom-Json).repositories
  $found = $false
  foreach ($r in $repos) {
    $tagsJson = Invoke-Aws @("ecr","list-tags-for-resource","--resource-arn",$r.repositoryArn)
    $tagsObj  = $null
    if ($tagsJson) { $tagsObj = ($tagsJson | ConvertFrom-Json).tags }
    $pairs    = ConvertTo-TagPairs $tagsObj
    if (-not (Has-TagKV $pairs "Project" $ProjectValue)) { continue }
    $found = $true

    $imgsJson = Invoke-Aws @("ecr","list-images","--repository-name",$r.repositoryName)
    $imgs = @()
    if ($imgsJson) { $imgs = ($imgsJson | ConvertFrom-Json).imageIds }
    if ($imgs -and -not $WhatIf) {
      Write-Host "ECR delete images: $($r.repositoryName) ($($imgs.Count))"
      [void](Invoke-Aws @("ecr","batch-delete-image","--repository-name",$r.repositoryName,"--image-ids",($imgs | ConvertTo-Json)))
    }

    Write-Host "ECR delete repo: $($r.repositoryName)"
    if (-not $WhatIf) { [void](Invoke-Aws @("ecr","delete-repository","--repository-name",$r.repositoryName,"--force")) }
  }
  if (-not $found) { Write-Host "No ECR repos with Project=$ProjectValue" }
}

function Remove-RDS {
  $deletedDbIds = @(); $deletedClusterIds = @(); $found = $false
  $dbsJson = Invoke-Aws @("rds","describe-db-instances")
  if ($dbsJson) {
    $dbs = ($dbsJson | ConvertFrom-Json).DBInstances
    foreach ($db in $dbs) {
      $tagsJson = Invoke-Aws @("rds","list-tags-for-resource","--resource-name",$db.DBInstanceArn)
      $tagsObj  = $null
      if ($tagsJson) { $tagsObj = ($tagsJson | ConvertFrom-Json).TagList }
      if (-not (Has-TagKV $tagsObj "Project" $ProjectValue)) { continue }
      $found = $true
      $name = $db.DBInstanceIdentifier
      Write-Host "RDS delete instance: $name"
      if (-not $WhatIf) {
        $cmd = @("rds","delete-db-instance","--db-instance-identifier",$name,"--delete-automated-backups")
        if ($SkipFinalSnapshots) { $cmd += "--skip-final-snapshot" }
        else {
          $snap = "$name-final-$(Get-Date -UFormat %s)"
          $cmd += @("--final-db-snapshot-identifier",$snap)
        }
        [void](Invoke-Aws $cmd)
        $deletedDbIds += $name
      }
    }
  }
  $clustersJson = Invoke-Aws @("rds","describe-db-clusters")
  if ($clustersJson) {
    $clusters = ($clustersJson | ConvertFrom-Json).DBClusters
    foreach ($cl in $clusters) {
      $tagsJson = Invoke-Aws @("rds","list-tags-for-resource","--resource-name",$cl.DBClusterArn)
      $tagsObj  = $null
      if ($tagsJson) { $tagsObj = ($tagsJson | ConvertFrom-Json).TagList }
      if (-not (Has-TagKV $tagsObj "Project" $ProjectValue)) { continue }
      $found = $true
      foreach ($m in $cl.DBClusterMembers) {
        Write-Host "RDS delete cluster member instance: $($m.DBInstanceIdentifier)"
        if (-not $WhatIf) {
          [void](Invoke-Aws @("rds","delete-db-instance","--db-instance-identifier",$m.DBInstanceIdentifier,"--delete-automated-backups","--skip-final-snapshot"))
          $deletedDbIds += $m.DBInstanceIdentifier
        }
      }
      Write-Host "RDS delete cluster: $($cl.DBClusterIdentifier)"
      if (-not $WhatIf) {
        $cmd = @("rds","delete-db-cluster","--db-cluster-identifier",$cl.DBClusterIdentifier)
        if ($SkipFinalSnapshots) { $cmd += "--skip-final-snapshot" }
        else {
          $snap = "$($cl.DBClusterIdentifier)-final-$(Get-Date -UFormat %s)"
          $cmd += @("--final-db-snapshot-identifier",$snap)
        }
        [void](Invoke-Aws $cmd)
        $deletedClusterIds += $cl.DBClusterIdentifier
      }
    }
  }
  if ($Wait -and -not $WhatIf) {
    foreach ($id in $deletedDbIds) {
      Write-Host "Waiting for DB instance to delete: $id"
      [void](Invoke-Aws @("rds","wait","db-instance-deleted","--db-instance-identifier",$id))
    }
    foreach ($cid in $deletedClusterIds) {
      Write-Host "Waiting for DB cluster to delete: $cid"
      [void](Invoke-Aws @("rds","wait","db-cluster-deleted","--db-cluster-identifier",$cid))
    }
  }
  $groupsJson = Invoke-Aws @("rds","describe-db-subnet-groups")
  if ($groupsJson) {
    foreach ($g in (($groupsJson | ConvertFrom-Json).DBSubnetGroups)) {
      if ($g.DBSubnetGroupName -notlike "*$Env*") { continue }
      Write-Host "RDS DB Subnet Group delete: $($g.DBSubnetGroupName)"
      if (-not $WhatIf) { [void](Invoke-Aws @("rds","delete-db-subnet-group","--db-subnet-group-name",$g.DBSubnetGroupName)) }
    }
  }
  if (-not $found) { Write-Host "No RDS instances/clusters/subnet groups for Project/Env" }
}

function Remove-DynamoDB {
  $listJson = Invoke-Aws @("dynamodb","list-tables")
  if (-not $listJson) { return }
  $found = $false
  foreach ($t in (($listJson | ConvertFrom-Json).TableNames)) {
    $descJson = Invoke-Aws @("dynamodb","describe-table","--table-name",$t)
    $arn = ($descJson | ConvertFrom-Json).Table.TableArn
    $tagsJson = Invoke-Aws @("dynamodb","list-tags-of-resource","--resource-arn",$arn)
    $tagsObj  = $null
    if ($tagsJson) { $tagsObj = ($tagsJson | ConvertFrom-Json).Tags }
    $pairs    = ConvertTo-TagPairs $tagsObj
    if (-not (Has-TagKV $pairs "Project" $ProjectValue)) { continue }
    $found = $true
    Write-Host "DynamoDB delete: $t"
    if (-not $WhatIf) { [void](Invoke-Aws @("dynamodb","delete-table","--table-name",$t)) }
  }
  if (-not $found) { Write-Host "No DynamoDB tables with Project=$ProjectValue" }
}

function Remove-SQSSNS {
  $qJson = Invoke-Aws @("sqs","list-queues")
  $queues = if ($qJson) { ($qJson | ConvertFrom-Json).QueueUrls } else { @() }
  $found = $false
  foreach ($url in $queues) {
    $tagsJson = Invoke-Aws @("sqs","list-queue-tags","--queue-url",$url)
    $tagsObj  = $null
    if ($tagsJson) { $tagsObj = ($tagsJson | ConvertFrom-Json).Tags }
    $pairs    = ConvertTo-TagPairs $tagsObj
    if (-not (Has-TagKV $pairs "Project" $ProjectValue)) { continue }
    $found = $true
    Write-Host "SQS delete: $url"
    if (-not $WhatIf) { [void](Invoke-Aws @("sqs","delete-queue","--queue-url",$url)) }
  }
  $tJson = Invoke-Aws @("sns","list-topics")
  if ($tJson) {
    foreach ($t in (($tJson | ConvertFrom-Json).Topics)) {
      $tagsJson = Invoke-Aws @("sns","list-tags-for-resource","--resource-arn",$t.TopicArn)
      $tagsObj  = $null
      if ($tagsJson) { $tagsObj = ($tagsJson | ConvertFrom-Json).Tags }
      $pairs    = ConvertTo-TagPairs $tagsObj
      if (-not (Has-TagKV $pairs "Project" $ProjectValue)) { continue }
      $found = $true
      Write-Host "SNS delete: $($t.TopicArn)"
      if (-not $WhatIf) { [void](Invoke-Aws @("sns","delete-topic","--topic-arn",$t.TopicArn)) }
    }
  }
  if (-not $found) { Write-Host "No SQS/SNS with Project=$ProjectValue" }
}

function Remove-CloudWatchLogs {
  $lgJson = Invoke-Aws @("logs","describe-log-groups")
  if (-not $lgJson) { return }
  $found = $false
  foreach ($lg in (($lgJson | ConvertFrom-Json).logGroups)) {
    $arn = $lg.arn
    if ($arn -match ':\*$') { $arn = $arn -replace ':\*$', '' }
    if (-not $arn -and $AccountId) { $arn = "arn:aws:logs:${Region}:${AccountId}:log-group:$($lg.logGroupName)" }
    $tagsJson = Invoke-Aws @("logs","list-tags-for-resource","--resource-arn",$arn)
    if (-not $tagsJson) { continue }
    $tagsObj  = ($tagsJson | ConvertFrom-Json).tags
    $pairs    = ConvertTo-TagPairs $tagsObj
    if (-not (Has-TagKV $pairs "Project" $ProjectValue)) { continue }
    $found = $true
    Write-Host "CloudWatch LogGroup delete: $($lg.logGroupName)"
    if (-not $WhatIf) { [void](Invoke-Aws @("logs","delete-log-group","--log-group-name",$lg.logGroupName)) }
  }
  if (-not $found) { Write-Host "No CloudWatch Log Groups with Project=$ProjectValue" }
}

function Remove-SSMParams {
  $paths = @("/","/app","/config","/secrets")
  $found = $false
  foreach ($p in $paths) {
    $pageJson = Invoke-Aws @("ssm","get-parameters-by-path","--path",$p,"--recursive")
    if (-not $pageJson) { continue }
    $page = $pageJson | ConvertFrom-Json
    foreach ($param in $page.Parameters) {
      $tagsJson = Invoke-Aws @("ssm","list-tags-for-resource","--resource-type","Parameter","--resource-id",$param.Name)
      $tagsObj  = $null
      if ($tagsJson) { $tagsObj = ($tagsJson | ConvertFrom-Json).TagList }
      $pairs    = ConvertTo-TagPairs $tagsObj
      if (-not (Has-TagKV $pairs "Project" $ProjectValue)) { continue }
      $found = $true
      Write-Host "SSM Parameter delete: $($param.Name)"
      if (-not $WhatIf) { [void](Invoke-Aws @("ssm","delete-parameter","--name",$param.Name)) }
    }
  }
  if (-not $found) { Write-Host "No SSM Parameters with Project=$ProjectValue" }
}

function Remove-SSMParamsByPathPrefix {
  $prefix = "/nhse-pps-wm/$Env/"
  $next = $null
  do {
    $args = @("ssm","get-parameters-by-path","--path",$prefix,"--recursive")
    if ($next) { $args += @("--next-token",$next) }
    $pageJson = Invoke-Aws $args
    if (-not $pageJson) { break }
    $obj = $pageJson | ConvertFrom-Json
    if ($obj.PSObject.Properties.Match('Parameters').Count -gt 0 -and $obj.Parameters) {
      foreach ($p in $obj.Parameters) {
        Write-Host "SSM Parameter delete: $($p.Name)"
        if (-not $WhatIf) { [void](Invoke-Aws @("ssm","delete-parameter","--name",$p.Name)) }
      }
    }
    if ($obj.PSObject.Properties.Match('NextToken').Count -gt 0 -and $obj.NextToken) { $next = $obj.NextToken } else { $next = $null }
  } while ($next)
}

function Remove-EFS {
  $efsJson = Invoke-Aws @("efs","describe-file-systems")
  if (-not $efsJson) { return }
  $found = $false
  foreach ($fs in (($efsJson | ConvertFrom-Json).FileSystems)) {
    $tagsJson = Invoke-Aws @("efs","describe-tags","--file-system-id",$fs.FileSystemId)
    $tagsObj  = $null
    if ($tagsJson) { $tagsObj = ($tagsJson | ConvertFrom-Json).Tags }
    $pairs    = ConvertTo-TagPairs $tagsObj
    if (-not (Has-TagKV $pairs "Project" $ProjectValue)) { continue }
    $found = $true
    $mtsJson = Invoke-Aws @("efs","describe-mount-targets","--file-system-id",$fs.FileSystemId)
    $mts = @()
    if ($mtsJson) { $mts = ($mtsJson | ConvertFrom-Json).MountTargets }
    foreach ($mt in $mts) {
      Write-Host "EFS mount target delete: $($mt.MountTargetId)"
      if (-not $WhatIf) { [void](Invoke-Aws @("efs","delete-mount-target","--mount-target-id",$mt.MountTargetId)) }
    }
    Write-Host "EFS delete: $($fs.FileSystemId)"
    if (-not $WhatIf) { [void](Invoke-Aws @("efs","delete-file-system","--file-system-id",$fs.FileSystemId)) }
  }
  if (-not $found) { Write-Host "No EFS file systems with Project=$ProjectValue" }
}

function Remove-Cognito {
  $poolsJson = Invoke-Aws @("cognito-idp","list-user-pools","--max-results","60")
  if (-not $poolsJson) { Write-Host "No Cognito user pools found"; return }
  $found = $false
  $pools = ($poolsJson | ConvertFrom-Json).UserPools
  foreach ($p in $pools) {
    $poolArn = "arn:aws:cognito-idp:${Region}:${AccountId}:userpool/$($p.Id)"
    $tagsJson = Invoke-Aws @("cognito-idp","list-tags-for-resource","--resource-arn",$poolArn)
    $tagsObj  = $null
    if ($tagsJson) { $tagsObj = ($tagsJson | ConvertFrom-Json).Tags }
    $pairs    = ConvertTo-TagPairs $tagsObj
    $match = $false
    if (Has-TagKV $pairs "Project" $ProjectValue) { $match = $true }
    if (-not $match -and $p.Name -like "*$Env*") { $match = $true }
    if (-not $match) { continue }
    $found = $true
    $clientsJson = Invoke-Aws @("cognito-idp","list-user-pool-clients","--user-pool-id",$p.Id,"--max-results","60")
    $clients = @()
    if ($clientsJson) { $clients = ($clientsJson | ConvertFrom-Json).UserPoolClients }
    foreach ($c in $clients) {
      Write-Host "Cognito user pool client delete: $($c.ClientId)"
      if (-not $WhatIf) { [void](Invoke-Aws @("cognito-idp","delete-user-pool-client","--user-pool-id",$p.Id,"--client-id",$c.ClientId)) }
    }
    $descJson = Invoke-Aws @("cognito-idp","describe-user-pool","--user-pool-id",$p.Id)
    if ($descJson) {
      $desc = $descJson | ConvertFrom-Json
      $domain = $null
      if ($desc.PSObject.Properties.Match('UserPool').Count -gt 0) {
        if ($desc.UserPool.PSObject.Properties.Match('Domain').Count -gt 0) { $domain = $desc.UserPool.Domain }
      }
      if ($domain) {
        Write-Host "Cognito hosted UI domain delete: $domain"
        if (-not $WhatIf) { [void](Invoke-Aws @("cognito-idp","delete-user-pool-domain","--user-pool-id",$p.Id,"--domain",$domain)) }
      }
    }
    Write-Host "Cognito user pool delete: $($p.Name) [$($p.Id)]"
    if (-not $WhatIf) { [void](Invoke-Aws @("cognito-idp","delete-user-pool","--user-pool-id",$p.Id)) }
  }
  if (-not $found) { Write-Host "No Cognito user pools with Project/Env" }
}

function Remove-CloudFrontAndWAF {
  # us-east-1 for CloudFront/WAF(CLOUDFRONT)
  $globalArgs = @("--region","us-east-1")
  if ($Profile) { $globalArgs += @("--profile",$Profile) }

  function Invoke-AwsGlobal([object[]]$ArgList) {
    if (-not $ArgList -or $ArgList.Count -eq 0) { return "" }
    $exe = "aws"
    $all = @($ArgList) + $globalArgs
    $flat = New-Object System.Collections.Generic.List[string]
    foreach ($a in $all) {
      if ($null -eq $a) { continue }
      if ($a -is [System.Collections.IEnumerable] -and -not ($a -is [string])) {
        foreach ($x in $a) { if ($null -ne $x) { [void]$flat.Add([string]$x) } }
      } else { [void]$flat.Add([string]$a) }
    }
    Write-Host ">> $exe $($flat -join ' ')"
    $op = ($ArgList.Count -ge 2) ? [string]$ArgList[1] : ""
    $isRead = $op -match '^(describe|get|list|wait)$'
    if ($WhatIf -and -not $isRead) { return "" }
    $out = & $exe @flat 2>&1
    if ($LASTEXITCODE -ne 0) {
      Write-Warning ("AWS CLI exited with {0}: {1}" -f $LASTEXITCODE, ($out -join "`n"))
      return ""
    }
    return ($out -join "`n")
  }

  $didAnything = $false

  # ---------- CloudFront distributions (pagination via --marker / NextMarker) ----------
  $marker = $null
  do {
    $args = @("cloudfront","list-distributions")
    if ($marker) { $args += @("--marker",$marker) }
    $distRaw = Invoke-AwsGlobal $args
    if (-not $distRaw) { break }

    $distDoc = $null
    try { $distDoc = $distRaw | ConvertFrom-Json } catch {}
    if (-not $distDoc) { break }

    $dlist = $null
    if ($distDoc.PSObject.Properties.Match('DistributionList').Count -gt 0) { $dlist = $distDoc.DistributionList }

    $items = @()
    if ($dlist -and $dlist.PSObject.Properties.Match('Items').Count -gt 0 -and $dlist.Items) {
      $items = $dlist.Items
    }

    foreach ($d in $items) {
      $arn = $d.ARN
      if (-not $arn) { continue }

      # read tags safely
      $tagsRaw = Invoke-AwsGlobal @("cloudfront","list-tags-for-resource","--resource",$arn)
      $pairs = @()
      if ($tagsRaw) {
        $tagsDoc = $null; try { $tagsDoc = $tagsRaw | ConvertFrom-Json } catch {}
        if ($tagsDoc -and $tagsDoc.PSObject.Properties.Match('Tags').Count -gt 0) {
          $itemsArr = if ($tagsDoc.Tags.PSObject.Properties.Match('Items').Count -gt 0) { $tagsDoc.Tags.Items } else { @() }
          $pairs = ConvertTo-TagPairs $itemsArr
        }
      }

      if (-not (Has-TagKV $pairs "Project" $ProjectValue)) { continue }
      $didAnything = $true

      # Best-effort WAF disassociation
      try {
        $wafRaw = Invoke-AwsGlobal @("wafv2","get-web-acl-for-resource","--resource-arn",$arn,"--scope","CLOUDFRONT")
        if ($wafRaw) {
          $wafDoc = $null; try { $wafDoc = $wafRaw | ConvertFrom-Json } catch {}
          $hasAcl = $false
          if ($wafDoc -and $wafDoc.PSObject.Properties.Match('WebACL').Count -gt 0 -and $wafDoc.WebACL) { $hasAcl = $true }
          if ($hasAcl -and -not $WhatIf) {
            Write-Host "Disassociate WAFv2 from CloudFront: $arn"
            [void](Invoke-AwsGlobal @("wafv2","disassociate-web-acl","--resource-arn",$arn,"--scope","CLOUDFRONT"))
          }
        }
      } catch {}

      # Get current config + ETag
      $cfgRaw1 = Invoke-AwsGlobal @("cloudfront","get-distribution-config","--id",$d.Id)
      if (-not $cfgRaw1) { continue }

      $cfgObj1 = $null
      try { $cfgObj1 = $cfgRaw1 | ConvertFrom-Json } catch {}
      if (-not $cfgObj1) { continue }

      $etag = $null
      if ($cfgObj1.PSObject.Properties.Match('ETag').Count -gt 0) { $etag = $cfgObj1.ETag }
      $cfg = $null
      if ($cfgObj1.PSObject.Properties.Match('DistributionConfig').Count -gt 0) { $cfg = $cfgObj1.DistributionConfig }

      $enabled = $false
      if ($cfg -and $cfg.PSObject.Properties.Match('Enabled').Count -gt 0) { $enabled = [bool]$cfg.Enabled }

      if ($enabled) {
        $cfg.Enabled = $false
        $tmp = Join-Path $env:TEMP ("cf-"+[guid]::NewGuid().ToString()+".json")
        $cfg | ConvertTo-Json -Depth 32 | Out-File -Encoding utf8 $tmp
        Write-Host "CloudFront disable: $($d.Id)"
        if (-not $WhatIf) {
          [void](Invoke-AwsGlobal @("cloudfront","update-distribution","--id",$d.Id,"--if-match",$etag,"--distribution-config","file://$tmp"))
        }
      }

      if ($Wait -and -not $WhatIf) {
        [void](Invoke-AwsGlobal @("cloudfront","wait","distribution-deployed","--id",$d.Id))
      }

      # Fresh ETag (no pipeline directly before 'if')
      $cfgRaw2 = Invoke-AwsGlobal @("cloudfront","get-distribution-config","--id",$d.Id)
      $etag2 = $etag
      if ($cfgRaw2) {
        $cfgObj2 = $null; try { $cfgObj2 = $cfgRaw2 | ConvertFrom-Json } catch {}
        if ($cfgObj2 -and $cfgObj2.PSObject.Properties.Match('ETag').Count -gt 0) { $etag2 = $cfgObj2.ETag }
      }

      Write-Host "CloudFront delete: $($d.Id)"
      if (-not $WhatIf) {
        [void](Invoke-AwsGlobal @("cloudfront","delete-distribution","--id",$d.Id,"--if-match",$etag2))
      }
    }

    # move to next page
    $marker = $null
    if ($dlist -and $dlist.PSObject.Properties.Match('NextMarker').Count -gt 0 -and $dlist.NextMarker) {
      $marker = $dlist.NextMarker
    }
  } while ($marker)

  # ---------- WAFv2 (CLOUDFRONT scope) ----------
  $wafsRaw = Invoke-AwsGlobal @("wafv2","list-web-acls","--scope","CLOUDFRONT")
  if ($wafsRaw) {
    $wafsDoc = $null; try { $wafsDoc = $wafsRaw | ConvertFrom-Json } catch {}
    if ($wafsDoc -and $wafsDoc.PSObject.Properties.Match('WebACLs').Count -gt 0) {
      foreach ($w in $wafsDoc.WebACLs) {
        $fullRaw = Invoke-AwsGlobal @("wafv2","get-web-acl","--scope","CLOUDFRONT","--id",$w.Id,"--name",$w.Name)
        if (-not $fullRaw) { continue }
        $full = $null; try { $full = $fullRaw | ConvertFrom-Json } catch {}
        if (-not $full) { continue }
        $webAclArn = $full.WebACL.ARN
        $lockToken = $full.LockToken

        $tagRaw = Invoke-AwsGlobal @("wafv2","list-tags-for-resource","--resource-arn",$webAclArn)
        $pairs = @()
        if ($tagRaw) {
          $tagDoc = $null; try { $tagDoc = $tagRaw | ConvertFrom-Json } catch {}
          if ($tagDoc -and $tagDoc.PSObject.Properties.Match('TagInfoForResource').Count -gt 0) {
            $pairs = ConvertTo-TagPairs $tagDoc.TagInfoForResource.TagList
          }
        }

        if (-not (Has-TagKV $pairs "Project" $ProjectValue)) { continue }
        Write-Host "WAFv2 WebACL (CloudFront) delete: $($w.Name)"
        if (-not $WhatIf) {
          [void](Invoke-AwsGlobal @("wafv2","delete-web-acl","--scope","CLOUDFRONT","--id",$w.Id,"--name",$w.Name,"--lock-token",$lockToken))
        }
        $didAnything = $true
      }
    }
  }

  # ---------- WAFv2 (REGIONAL) ----------
  $regRaw = Invoke-Aws @("wafv2","list-web-acls","--scope","REGIONAL")
  if ($regRaw) {
    $regDoc = $null; try { $regDoc = $regRaw | ConvertFrom-Json } catch {}
    if ($regDoc -and $regDoc.PSObject.Properties.Match('WebACLs').Count -gt 0) {
      foreach ($w in $regDoc.WebACLs) {
        $fullRaw = Invoke-Aws @("wafv2","get-web-acl","--scope","REGIONAL","--id",$w.Id,"--name",$w.Name)
        if (-not $fullRaw) { continue }
        $full = $null; try { $full = $fullRaw | ConvertFrom-Json } catch {}
        if (-not $full) { continue }

        $webAclArn = $full.WebACL.ARN
        $lockToken = $full.LockToken

        $tagRaw = Invoke-Aws @("wafv2","list-tags-for-resource","--resource-arn",$webAclArn)
        $pairs = @()
        if ($tagRaw) {
          $tagDoc = $null; try { $tagDoc = $tagRaw | ConvertFrom-Json } catch {}
          if ($tagDoc -and $tagDoc.PSObject.Properties.Match('TagInfoForResource').Count -gt 0) {
            $pairs = ConvertTo-TagPairs $tagDoc.TagInfoForResource.TagList
          }
        }

        if (-not (Has-TagKV $pairs "Project" $ProjectValue)) { continue }
        Write-Host "WAFv2 WebACL (Regional) delete: $($w.Name)"
        if (-not $WhatIf) {
          [void](Invoke-Aws @("wafv2","delete-web-acl","--scope","REGIONAL","--id",$w.Id,"--name",$w.Name,"--lock-token",$lockToken))
        }
        $didAnything = $true
      }
    }
  }

  if (-not $didAnything) { Write-Host "No CloudFront/WAF resources with Project=$ProjectValue" }
}

function Remove-VPCStacks {
  $vpcsJson = Invoke-Aws @("ec2","describe-vpcs","--filters","Name=tag:Project,Values=$ProjectValue")
  if (-not $vpcsJson) { return }
  $vpcs = ($vpcsJson | ConvertFrom-Json).Vpcs
  if (-not $vpcs -or $vpcs.Count -eq 0) { Write-Host "No VPCs with Project=$ProjectValue"; return }
  foreach ($vpc in $vpcs) {
    $vpcId = $vpc.VpcId
    Write-Host "VPC teardown: $vpcId"

    $eniJson = Invoke-Aws @("ec2","describe-network-interfaces","--filters","Name=vpc-id,Values=$vpcId")
    $enis = if ($eniJson) { ($eniJson | ConvertFrom-Json).NetworkInterfaces } else { @() }
    foreach ($eni in $enis) {
      if ($eni.Status -eq "in-use") { continue }
      Write-Host "  ENI delete: $($eni.NetworkInterfaceId)"
      if (-not $WhatIf) { [void](Invoke-Aws @("ec2","delete-network-interface","--network-interface-id",$eni.NetworkInterfaceId)) }
    }

    $sgJson = Invoke-Aws @("ec2","describe-security-groups","--filters","Name=vpc-id,Values=$vpcId")
    $sgs = if ($sgJson) { ($sgJson | ConvertFrom-Json).SecurityGroups } else { @() }
    foreach ($sg in $sgs) {
      if ($sg.GroupName -eq "default") { continue }
      Write-Host "  SG delete: $($sg.GroupId) ($($sg.GroupName))"
      if (-not $WhatIf) { [void](Invoke-Aws @("ec2","delete-security-group","--group-id",$sg.GroupId)) }
    }

    $rtJson = Invoke-Aws @("ec2","describe-route-tables","--filters","Name=vpc-id,Values=$vpcId")
    $rts = if ($rtJson) { ($rtJson | ConvertFrom-Json).RouteTables } else { @() }
    foreach ($rt in $rts) {
      $isMain = $false
      foreach ($assoc in $rt.Associations) { if ($assoc.Main) { $isMain = $true } }
      if ($isMain) { continue }
      foreach ($assoc in $rt.Associations) {
        if (-not $assoc.Main) {
          Write-Host "  RT disassociate: $($assoc.RouteTableAssociationId)"
          if (-not $WhatIf) { [void](Invoke-Aws @("ec2","disassociate-route-table","--association-id",$assoc.RouteTableAssociationId)) }
        }
      }
      Write-Host "  RT delete: $($rt.RouteTableId)"
      if (-not $WhatIf) { [void](Invoke-Aws @("ec2","delete-route-table","--route-table-id",$rt.RouteTableId)) }
    }

    $naclJson = Invoke-Aws @("ec2","describe-network-acls","--filters","Name=vpc-id,Values=$vpcId")
    $nacls = if ($naclJson) { ($naclJson | ConvertFrom-Json).NetworkAcls } else { @() }
    foreach ($nacl in $nacls) {
      if ($nacl.IsDefault) { continue }
      Write-Host "  NACL delete: $($nacl.NetworkAclId)"
      if (-not $WhatIf) { [void](Invoke-Aws @("ec2","delete-network-acl","--network-acl-id",$nacl.NetworkAclId)) }
    }

    $subJson = Invoke-Aws @("ec2","describe-subnets","--filters","Name=vpc-id,Values=$vpcId")
    $subs = if ($subJson) { ($subJson | ConvertFrom-Json).Subnets } else { @() }
    foreach ($s in $subs) {
      Write-Host "  Subnet delete: $($s.SubnetId)"
      if (-not $WhatIf) { [void](Invoke-Aws @("ec2","delete-subnet","--subnet-id",$s.SubnetId)) }
    }

    $igwJson = Invoke-Aws @("ec2","describe-internet-gateways","--filters","Name=attachment.vpc-id,Values=$vpcId")
    $igws = if ($igwJson) { ($igwJson | ConvertFrom-Json).InternetGateways } else { @() }
    foreach ($igw in $igws) {
      Write-Host "  IGW detach & delete: $($igw.InternetGatewayId)"
      if (-not $WhatIf) {
        [void](Invoke-Aws @("ec2","detach-internet-gateway","--internet-gateway-id",$igw.InternetGatewayId,"--vpc-id",$vpcId))
        [void](Invoke-Aws @("ec2","delete-internet-gateway","--internet-gateway-id",$igw.InternetGatewayId))
      }
    }

    Write-Host "VPC delete: $vpcId"
    if (-not $WhatIf) { [void](Invoke-Aws @("ec2","delete-vpc","--vpc-id",$vpcId)) }
  }
}

function Remove-IAMPolicies {
  # IAM is global; region is ignored by AWS CLI. We still pass it for consistency.
  $polNext = $null
  do {
    $args = @("iam","list-policies","--scope","Local")
    if ($polNext) { $args += @("--marker",$polNext) }

    $raw = Invoke-Aws $args
    if (-not $raw) { break }

    $doc = $null; try { $doc = $raw | ConvertFrom-Json } catch {}
    if (-not $doc) { break }

    $pols = if ($doc.PSObject.Properties.Match('Policies').Count -gt 0) { $doc.Policies } else { @() }

    foreach ($p in $pols) {
      # Check tags (may be empty)
      $tagsRaw = Invoke-Aws @("iam","list-policy-tags","--policy-arn",$p.Arn)
      $pairs = @()
      if ($tagsRaw) {
        $tagsDoc = $null; try { $tagsDoc = $tagsRaw | ConvertFrom-Json } catch {}
        if ($tagsDoc -and $tagsDoc.PSObject.Properties.Match('Tags').Count -gt 0) {
          $pairs = ConvertTo-TagPairs $tagsDoc.Tags
        }
      }

      $match = $false
      if (Has-TagKV $pairs "Project" $ProjectValue) { $match = $true }
      if (-not $match -and $p.PolicyName -like "*$Env*") { $match = $true }
      if (-not $match) { continue }

      # Detach from roles
      $entRaw = Invoke-Aws @("iam","list-entities-for-policy","--policy-arn",$p.Arn)
      $ent = $null; try { $ent = $entRaw | ConvertFrom-Json } catch {}
      $roles  = if ($ent -and $ent.PSObject.Properties.Match('PolicyRoles').Count  -gt 0) { $ent.PolicyRoles } else { @() }
      $users  = if ($ent -and $ent.PSObject.Properties.Match('PolicyUsers').Count  -gt 0) { $ent.PolicyUsers } else { @() }
      $groups = if ($ent -and $ent.PSObject.Properties.Match('PolicyGroups').Count -gt 0) { $ent.PolicyGroups } else { @() }

      foreach ($r in $roles) {
        Write-Host "IAM detach policy from role: $($p.PolicyName) -> $($r.RoleName)"
        if (-not $WhatIf) { [void](Invoke-Aws @("iam","detach-role-policy","--role-name",$r.RoleName,"--policy-arn",$p.Arn)) }
      }
      foreach ($u in $users) {
        Write-Host "IAM detach policy from user: $($p.PolicyName) -> $($u.UserName)"
        if (-not $WhatIf) { [void](Invoke-Aws @("iam","detach-user-policy","--user-name",$u.UserName,"--policy-arn",$p.Arn)) }
      }
      foreach ($g in $groups) {
        Write-Host "IAM detach policy from group: $($p.PolicyName) -> $($g.GroupName)"
        if (-not $WhatIf) { [void](Invoke-Aws @("iam","detach-group-policy","--group-name",$g.GroupName,"--policy-arn",$p.Arn)) }
      }

      # Delete all NON-default versions first (no JMESPath; filter in PS)
      $versRaw = Invoke-Aws @("iam","list-policy-versions","--policy-arn",$p.Arn)
      $versDoc = $null; try { $versDoc = $versRaw | ConvertFrom-Json } catch {}
      $vers = if ($versDoc -and $versDoc.PSObject.Properties.Match('Versions').Count -gt 0) { $versDoc.Versions } else { @() }
      $nonDefault = $vers | Where-Object { $_.IsDefaultVersion -ne $true -and $_.VersionId }

      foreach ($v in $nonDefault) {
        Write-Host "IAM delete policy version: $($p.PolicyName) v$($v.VersionId)"
        if (-not $WhatIf) { [void](Invoke-Aws @("iam","delete-policy-version","--policy-arn",$p.Arn,"--version-id",$v.VersionId)) }
      }

      # Now delete the policy
      Write-Host "IAM delete policy: $($p.PolicyName)"
      if (-not $WhatIf) { [void](Invoke-Aws @("iam","delete-policy","--policy-arn",$p.Arn)) }
    }

    # Pagination (IAM: IsTruncated + Marker)
    $polNext = $null
    if ($doc.PSObject.Properties.Match('IsTruncated').Count -gt 0 -and $doc.IsTruncated `
        -and $doc.PSObject.Properties.Match('Marker').Count -gt 0 -and $doc.Marker) {
      $polNext = $doc.Marker
    }
  } while ($polNext)
}

function Invoke-EcsDeleteTaskDefs {
  param([string[]]$Arns)

  if (-not $Arns -or $Arns.Count -eq 0) { return }
  $chunks = @()
  for ($i=0; $i -lt $Arns.Count; $i+=10) { $chunks += ,($Arns[$i..([Math]::Min($i+9,$Arns.Count-1))]) }

  foreach ($chunk in $chunks) {
    Write-Host "ECS delete-task-definitions: $($chunk -join ', ')"
    if (-not $WhatIf) {
      $raw = Invoke-Aws (@("ecs","delete-task-definitions","--task-definitions") + $chunk)
      if (-not $raw) { continue }
      try {
        $doc = $raw | ConvertFrom-Json
        # If any failed (bad status), try a deregister-then-delete retry on those
        $failed = @()
        if ($doc.PSObject.Properties.Match('failures').Count -gt 0 -and $doc.failures) {
          foreach ($f in $doc.failures) {
            if ($f.arn) { $failed += [string]$f.arn }
          }
        }
        foreach ($farn in $failed) {
          Write-Host "ECS deregister fallback (then delete): $farn"
          [void](Invoke-Aws @("ecs","deregister-task-definition","--task-definition",$farn))
          [void](Invoke-Aws @("ecs","delete-task-definitions","--task-definitions",$farn))
        }
      } catch { }
    }
  }
}

# ------------------ Step Runner ------------------

$steps = @(
  @{ Name = "EC2 Instances";                 Action = { Remove-EC2Instances } },
  @{ Name = "Auto Scaling Groups";           Action = { Remove-ASG } },
  @{ Name = "ECS (clusters/services by tag)";Action = { Remove-ECS } },
  @{ Name = "ECS Task Definitions (by tag)"; Action = { Remove-ECSTaskDefsByTag } },
  @{ Name = "ECS Fallback (names/defs)";     Action = { Remove-ECSTaskDefsAndClusterByName } },
  @{ Name = "Lambda";                        Action = { Remove-Lambda } },
  @{ Name = "Elastic Load Balancing v2";     Action = { Remove-ELBv2 } },
  @{ Name = "Orphan Target Groups";          Action = { Remove-OrphanTargetGroups } },
  @{ Name = "API Gateway";                   Action = { Remove-ApiGateway } },
  @{ Name = "VPC Endpoints & NAT GW";        Action = { Remove-VPCEndpointsAndNAT } },
  @{ Name = "Elastic IPs";                   Action = { Remove-EIPs } },
  @{ Name = "S3 Buckets";                    Action = { Remove-S3 } },
  @{ Name = "ECR Repositories";              Action = { Remove-ECR } },
  @{ Name = "RDS Instances/Subnet Groups";   Action = { Remove-RDS } },
  @{ Name = "DynamoDB Tables";               Action = { Remove-DynamoDB } },
  @{ Name = "SQS & SNS";                     Action = { Remove-SQSSNS } },
  @{ Name = "CloudWatch Log Groups";         Action = { Remove-CloudWatchLogs } },
  @{ Name = "SSM Parameters (tagged)";       Action = { Remove-SSMParams } },
  @{ Name = "SSM Params (path prefix)";      Action = { Remove-SSMParamsByPathPrefix } },
  @{ Name = "EFS";                           Action = { Remove-EFS } },
  @{ Name = "Cognito";                       Action = { Remove-Cognito } },
  @{ Name = "CloudFront & WAFv2";            Action = { Remove-CloudFrontAndWAF } },
  @{ Name = "VPC Core";                      Action = { Remove-VPCStacks } },
  @{ Name = "IAM Managed Policies";          Action = { Remove-IAMPolicies } }
)

foreach ($s in $steps) {
  Write-Host ("=== Step: {0} ===" -f $s.Name) -ForegroundColor Green
  try { & $s.Action } catch { Write-Warning "Step '$($s.Name)' failed: $($_.Exception.Message)" }
}

Write-Host "Cleanup complete."
