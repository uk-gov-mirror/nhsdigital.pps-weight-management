# Test configuration for CloudFront module
variables {
  name                      = "test-distribution"
  alb_dns_name              = "test-alb-123456789.us-east-1.elb.amazonaws.com"
  custom_header_value       = "test-secret-value"
  price_class               = "PriceClass_100"
  web_acl_id                = ""
  default_root_object       = "index.html"
  aliases                   = ["example.com", "www.example.com"]
  default_ttl               = 3600
  max_ttl                   = 86400
  acm_certificate_arn       = ""
  geo_restriction_type      = "none"
  geo_restriction_locations = []
  ordered_cache_behaviors   = []
  custom_error_responses    = []
  tags = {
    Environment = "test"
    Project     = "cloudfront-test"
  }
}

# Test 1: Basic CloudFront distribution creation
run "test_basic_cloudfront_creation" {
  command = plan

  assert {
    condition     = aws_cloudfront_distribution.main.enabled == true
    error_message = "CloudFront distribution should be enabled"
  }

  assert {
    condition     = aws_cloudfront_distribution.main.is_ipv6_enabled == true
    error_message = "IPv6 should be enabled"
  }

  assert {
    condition     = aws_cloudfront_distribution.main.comment == "CloudFront distribution for test-distribution"
    error_message = "Comment should include the distribution name"
  }

  assert {
    condition     = aws_cloudfront_distribution.main.http_version == "http2and3"
    error_message = "HTTP version should be http2and3"
  }
}

# Test 2: Origin configuration
run "test_origin_configuration" {
  command = plan

  assert {
    condition     = length([for origin in aws_cloudfront_distribution.main.origin : origin if origin.origin_id == "alb"]) == 1
    error_message = "Should have exactly one origin with ID 'alb'"
  }

  assert {
    condition     = [for origin in aws_cloudfront_distribution.main.origin : origin.domain_name if origin.origin_id == "alb"][0] == "test-alb-123456789.us-east-1.elb.amazonaws.com"
    error_message = "Origin domain name should match ALB DNS name"
  }

  assert {
    condition     = [for origin in aws_cloudfront_distribution.main.origin : origin.custom_origin_config[0].origin_protocol_policy if origin.origin_id == "alb"][0] == "http-only"
    error_message = "Origin protocol policy should be http-only"
  }

  assert {
    condition     = contains([for origin in aws_cloudfront_distribution.main.origin : origin.custom_origin_config[0].origin_ssl_protocols if origin.origin_id == "alb"][0], "TLSv1.2")
    error_message = "Origin SSL protocols should include TLSv1.2"
  }
}

# Test 3: Custom header configuration
run "test_custom_header" {
  command = plan

  assert {
    condition = length([
      for origin in aws_cloudfront_distribution.main.origin :
      origin if origin.origin_id == "alb" && length([
        for header in origin.custom_header :
        header if header.name == "X-Custom-Header" && header.value == "test-secret-value"
      ]) > 0
    ]) == 1
    error_message = "Should have origin with custom header X-Custom-Header set to test-secret-value"
  }
}

# Test 4: Default cache behavior
run "test_default_cache_behavior" {
  command = plan

  assert {
    condition     = length(aws_cloudfront_distribution.main.default_cache_behavior[0].allowed_methods) == 7
    error_message = "Should allow all HTTP methods"
  }

  assert {
    condition     = contains(aws_cloudfront_distribution.main.default_cache_behavior[0].allowed_methods, "GET")
    error_message = "Should allow GET method"
  }

  assert {
    condition     = aws_cloudfront_distribution.main.default_cache_behavior[0].target_origin_id == "alb"
    error_message = "Target origin ID should be 'alb'"
  }

  assert {
    condition     = aws_cloudfront_distribution.main.default_cache_behavior[0].viewer_protocol_policy == "redirect-to-https"
    error_message = "Should redirect to HTTPS"
  }

  assert {
    condition     = aws_cloudfront_distribution.main.default_cache_behavior[0].compress == true
    error_message = "Compression should be enabled"
  }
}

# Test 5: Certificate configuration with default certificate
run "test_default_certificate" {
  command = plan

  assert {
    condition     = aws_cloudfront_distribution.main.viewer_certificate[0].cloudfront_default_certificate == true
    error_message = "Should use CloudFront default certificate when ACM ARN is empty"
  }

  assert {
    condition     = aws_cloudfront_distribution.main.viewer_certificate[0].acm_certificate_arn == null
    error_message = "ACM certificate ARN should be null when not provided"
  }
}

# Test 6: Test with custom SSL certificate
run "test_custom_certificate" {
  command = plan

  variables {
    acm_certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012"
  }

  assert {
    condition     = aws_cloudfront_distribution.main.viewer_certificate[0].cloudfront_default_certificate == false
    error_message = "Should not use default certificate when ACM ARN is provided"
  }

  assert {
    condition     = aws_cloudfront_distribution.main.viewer_certificate[0].acm_certificate_arn == "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012"
    error_message = "Should use provided ACM certificate ARN"
  }

  assert {
    condition     = aws_cloudfront_distribution.main.viewer_certificate[0].ssl_support_method == "sni-only"
    error_message = "Should use SNI-only SSL support method"
  }

  assert {
    condition     = aws_cloudfront_distribution.main.viewer_certificate[0].minimum_protocol_version == "TLSv1.2_2021"
    error_message = "Should use TLSv1.2_2021 as minimum protocol version"
  }
}

# Test 7: Test with ordered cache behaviors
run "test_ordered_cache_behaviors" {
  command = plan

  variables {
    ordered_cache_behaviors = [
      {
        path_pattern         = "/api/*"
        allowed_methods      = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
        cached_methods       = ["GET", "HEAD"]
        forward_query_string = true
        forward_headers      = ["Authorization", "Host"]
        forward_cookies      = "none"
        min_ttl              = 0
        default_ttl          = 0
        max_ttl              = 0
      }
    ]
  }

  assert {
    condition     = length(aws_cloudfront_distribution.main.ordered_cache_behavior) == 1
    error_message = "Should create one ordered cache behavior"
  }

  assert {
    condition     = aws_cloudfront_distribution.main.ordered_cache_behavior[0].path_pattern == "/api/*"
    error_message = "Path pattern should match configuration"
  }

  assert {
    condition     = aws_cloudfront_distribution.main.ordered_cache_behavior[0].target_origin_id == "alb"
    error_message = "Target origin ID should be 'alb'"
  }
}

// ...existing code...

# Test 8: Test with custom error responses
run "test_custom_error_responses" {
  command = plan

  variables {
    custom_error_responses = [
      {
        error_code            = 404
        response_code         = 200
        response_page_path    = "/index.html"
        error_caching_min_ttl = 300
      }
    ]
  }

  assert {
    condition     = length(aws_cloudfront_distribution.main.custom_error_response) == 1
    error_message = "Should create one custom error response"
  }

  assert {
    condition = length([
      for error_response in aws_cloudfront_distribution.main.custom_error_response :
      error_response if error_response.error_code == 404
    ]) == 1
    error_message = "Should have a custom error response for error code 404"
  }

  assert {
    condition = [
      for error_response in aws_cloudfront_distribution.main.custom_error_response :
      error_response.response_code if error_response.error_code == 404
    ][0] == 200
    error_message = "Response code should be 200 for 404 errors"
  }

  assert {
    condition = [
      for error_response in aws_cloudfront_distribution.main.custom_error_response :
      error_response.response_page_path if error_response.error_code == 404
    ][0] == "/index.html"
    error_message = "Response page path should be /index.html for 404 errors"
  }
}

# Test 9: Test geo restrictions
run "test_geo_restrictions" {
  command = plan

  variables {
    geo_restriction_type      = "blacklist"
    geo_restriction_locations = ["CN", "RU"]
  }

  assert {
    condition     = aws_cloudfront_distribution.main.restrictions[0].geo_restriction[0].restriction_type == "blacklist"
    error_message = "Geo restriction type should be blacklist"
  }

  assert {
    condition     = contains(aws_cloudfront_distribution.main.restrictions[0].geo_restriction[0].locations, "CN")
    error_message = "Should include CN in restricted locations"
  }
}

# Test 10: Test tags
run "test_tags" {
  command = plan

  assert {
    condition     = aws_cloudfront_distribution.main.tags["Environment"] == "test"
    error_message = "Environment tag should be set to test"
  }

  assert {
    condition     = aws_cloudfront_distribution.main.tags["Project"] == "cloudfront-test"
    error_message = "Project tag should be set correctly"
  }
}

# Test 11: Test aliases configuration
run "test_aliases" {
  command = plan

  assert {
    condition     = length(aws_cloudfront_distribution.main.aliases) == 2
    error_message = "Should have 2 aliases"
  }

  assert {
    condition     = contains(aws_cloudfront_distribution.main.aliases, "example.com")
    error_message = "Should contain example.com alias"
  }

  assert {
    condition     = contains(aws_cloudfront_distribution.main.aliases, "www.example.com")
    error_message = "Should contain www.example.com alias"
  }
}