data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "backend_lambda" {
  name               = "${var.app_name}-${var.environment}-backend-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

# Attach VPC execution role for CloudWatch logs and ENI creation
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.backend_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Policy for DynamoDB, S3, and Bedrock
data "aws_iam_policy_document" "backend_permissions" {
  statement {
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem"
    ]
    resources = [
      aws_dynamodb_table.transactions.arn,
      "${aws_dynamodb_table.transactions.arn}/index/*",
      aws_dynamodb_table.users.arn,
      "${aws_dynamodb_table.users.arn}/index/*"
    ]
  }

  statement {
    actions = [
      "s3:PutObject",
      "s3:GetObject"
    ]
    resources = ["${aws_s3_bucket.uploads.arn}/*"]
  }

  statement {
    actions = [
      "kms:Decrypt",
      "kms:GenerateDataKey"
    ]
    resources = [aws_kms_key.s3_key.arn]
  }

  statement {
    actions = [
      "bedrock:InvokeModel"
    ]
    resources = [
      "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-*",
      "arn:aws:bedrock:us-*:*:inference-profile/us.anthropic.claude-*"
    ]
  }

  statement {
    actions = [
      "textract:DetectDocumentText"
    ]
    resources = ["*"]
    # NOTE: Textract DetectDocumentText (synchronous) does NOT support
    # resource-level permissions — AWS requires Resource: "*".
    # See: https://docs.aws.amazon.com/textract/latest/dg/security_iam_service-with-iam.html
  }
}

resource "aws_iam_policy" "backend_policy" {
  name   = "${var.app_name}-${var.environment}-backend-policy"
  policy = data.aws_iam_policy_document.backend_permissions.json
}

resource "aws_iam_role_policy_attachment" "backend_custom_policy_attach" {
  role       = aws_iam_role.backend_lambda.name
  policy_arn = aws_iam_policy.backend_policy.arn
}

# Dummy archive to provision the lambda (user will update code later)
data "archive_file" "dummy_lambda" {
  type        = "zip"
  output_path = "${path.module}/dummy.zip"
  source {
    content  = "def handler(event, context): return {'statusCode': 200}"
    filename = "app.py"
  }
}

locals {
  backend_package_zip = abspath("${path.module}/../package.zip")
}

resource "aws_lambda_function" "backend" {
  function_name = "${var.app_name}-${var.environment}-backend"
  role          = aws_iam_role.backend_lambda.arn
  handler       = "src.app.handler"
  runtime       = "python3.11"
  architectures = ["arm64"]
  timeout       = 30
  memory_size   = 512

  filename         = local.backend_package_zip
  source_code_hash = filebase64sha256(local.backend_package_zip)

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      AI_BACKEND        = "hybrid"
      AI_MODEL_ID       = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
      STORAGE_BACKEND   = "s3"
      STORAGE_BUCKET    = aws_s3_bucket.uploads.id
      USERSTORE_BACKEND = "dynamodb"
      USERSTORE_TABLE   = aws_dynamodb_table.transactions.name
      USERS_TABLE       = aws_dynamodb_table.users.name
      JWT_SECRET        = "budgetbot-jwt-secret-2026"
      JWT_EXP_MINUTES   = "60"
      CORS_ORIGINS      = "https://${aws_cloudfront_distribution.api_cdn.domain_name},http://localhost:5173"
    }
  }
}

output "lambda_function_name" {
  value = aws_lambda_function.backend.function_name
}
