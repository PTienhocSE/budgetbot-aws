resource "aws_sns_topic" "alerts" {
  name = "${var.app_name}-${var.environment}-alerts"
}

resource "aws_cloudwatch_log_group" "api_logs" {
  name              = "/aws/apigateway/${aws_apigatewayv2_api.http_api.name}"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.backend.function_name}"
  retention_in_days = 14
}

# Example Cost Guard Lambda (Dummy for now, triggers via EventBridge)
resource "aws_lambda_function" "cost_guard" {
  function_name = "${var.app_name}-${var.environment}-cost-guard"
  role          = aws_iam_role.backend_lambda.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  filename      = data.archive_file.dummy_lambda.output_path
}

resource "aws_cloudwatch_event_rule" "daily_cost_check" {
  name                = "${var.app_name}-daily-cost-check"
  schedule_expression = "rate(1 day)"
}

resource "aws_cloudwatch_event_target" "cost_guard_target" {
  rule      = aws_cloudwatch_event_rule.daily_cost_check.name
  target_id = "CostGuard"
  arn       = aws_lambda_function.cost_guard.arn
}

resource "aws_lambda_permission" "allow_eventbridge_cost_guard" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_guard.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_cost_check.arn
}

resource "aws_budgets_budget" "budgetbot_budget" {
  name         = "${var.app_name}-${var.environment}-monthly-100usd"
  budget_type  = "COST"
  limit_amount = "100"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [aws_sns_topic.alerts.arn]
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.app_name}-${var.environment}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Alarm if Lambda errors occur"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.backend.function_name
  }
}
