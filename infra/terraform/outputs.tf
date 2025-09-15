output "cloudfront_url"             { value = "https://${aws_cloudfront_distribution.cdn.domain_name}" }
output "cloudfront_distribution_id" { value = aws_cloudfront_distribution.cdn.id }
output "api_endpoint"               { value = aws_apigatewayv2_api.http_api.api_endpoint }
output "cognito_issuer"             { value = "https://cognito-idp.${data.aws_region.current.name}.amazonaws.com/${aws_cognito_user_pool.up.id}" }
output "cognito_user_pool_id"       { value = aws_cognito_user_pool.up.id }
output "cognito_client_id_ci"       { value = aws_cognito_user_pool_client.ci.id }
output "cognito_client_id_spa"      { value = aws_cognito_user_pool_client.spa.id }
output "website_bucket"             { value = aws_s3_bucket.site.id }
output "origin_secret"              { 
  value = random_string.origin_secret.result 
  sensitive = true 
}