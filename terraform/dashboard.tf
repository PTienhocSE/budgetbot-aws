resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.app_name}-${var.environment}-dashboard"
  dashboard_body = <<EOF
{
  "widgets": [
    {
      "type": "metric",
      "x": 0,
      "y": 0,
      "width": 12,
      "height": 8,
      "properties": {
        "metrics": [
          [ "AWS/Lambda", "Invocations", "FunctionName", "${aws_lambda_function.backend.function_name}", { "stat": "Sum" } ],
          [ ".", "Errors", ".", ".", { "stat": "Sum" } ],
          [ ".", "Invocations", ".", "${aws_lambda_function.file_processor.function_name}", { "stat": "Sum" } ],
          [ ".", "Errors", ".", ".", { "stat": "Sum" } ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "us-east-1",
        "title": "Lambda Activity"
      }
    },
    {
      "type": "metric",
      "x": 12,
      "y": 0,
      "width": 12,
      "height": 8,
      "properties": {
        "metrics": [
          [ "AWS/ApiGateway", "Count", "ApiId", "${aws_apigatewayv2_api.http_api.id}", { "stat": "Sum" } ],
          [ ".", "4XXError", ".", ".", { "stat": "Sum" } ],
          [ ".", "5XXError", ".", ".", { "stat": "Sum" } ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "us-east-1",
        "title": "API Gateway Traffic"
      }
    }
  ]
}
EOF
}
