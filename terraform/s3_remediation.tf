resource "aws_lambda_function" "s3_remediation" {
  function_name = "${var.app_name}-${var.environment}-s3-remediation"
  role          = aws_iam_role.s3_remediation_role.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  filename      = data.archive_file.dummy_lambda.output_path
  timeout       = 10
}

resource "aws_iam_role" "s3_remediation_role" {
  name = "${var.app_name}-${var.environment}-s3-remediation-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "s3_remediation_policy" {
  name = "${var.app_name}-${var.environment}-s3-remediation-policy"
  role = aws_iam_role.s3_remediation_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:PutBucketPublicAccessBlock",
          "s3:GetBucketPublicAccessBlock"
        ]
        Effect   = "Allow"
        Resource = aws_s3_bucket.uploads.arn
      },
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# EventBridge rule to detect changes to S3 Public Access Block via CloudTrail
resource "aws_cloudwatch_event_rule" "s3_pab_change" {
  name        = "${var.app_name}-${var.environment}-s3-pab-change"
  description = "Triggers when S3 Public Access Block is modified"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["AWS API Call via CloudTrail"]
    detail = {
      eventSource = ["s3.amazonaws.com"]
      eventName = [
        "DeleteBucketPublicAccessBlock",
        "PutBucketPublicAccessBlock"
      ]
      requestParameters = {
        bucketName = [aws_s3_bucket.uploads.id]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "trigger_remediation" {
  rule      = aws_cloudwatch_event_rule.s3_pab_change.name
  target_id = "TriggerS3Remediation"
  arn       = aws_lambda_function.s3_remediation.arn
}

resource "aws_lambda_permission" "allow_eventbridge_s3_remediation" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.s3_remediation.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.s3_pab_change.arn
}
