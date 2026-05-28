data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.app_name}-${var.environment}-vpc"
  }
}

# --- Subnets across 2 AZs (Multi-AZ) ---
resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "${var.app_name}-${var.environment}-subnet-private-a"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = {
    Name = "${var.app_name}-${var.environment}-subnet-private-b"
  }
}

# --- Route Table ---
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.app_name}-${var.environment}-rt-private"
  }
}

resource "aws_route_table_association" "private_a" {
  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_b" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private.id
}

# --- Security Groups ---
resource "aws_security_group" "lambda" {
  name        = "${var.app_name}-${var.environment}-lambda-sg"
  description = "Security group for backend Lambda function"
  vpc_id      = aws_vpc.main.id

  # Allow all outbound traffic to reach VPC Endpoints (and other resources if needed)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.app_name}-${var.environment}-lambda-sg"
  }
}

resource "aws_security_group" "bedrock" {
  name        = "${var.app_name}-${var.environment}-bedrock-sg"
  description = "Security group for Bedrock Runtime Interface Endpoint"
  vpc_id      = aws_vpc.main.id

  # Allow inbound HTTPS traffic from Lambda SG
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }

  tags = {
    Name = "${var.app_name}-${var.environment}-bedrock-sg"
  }
}

# --- Gateway Endpoints (Free) ---
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = {
    Name = "${var.app_name}-${var.environment}-vpce-s3"
  }
}

resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.dynamodb"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = {
    Name = "${var.app_name}-${var.environment}-vpce-dynamodb"
  }
}

# --- Interface Endpoint for Bedrock Runtime (Costs ~$0.013/hour) ---
resource "aws_vpc_endpoint" "bedrock" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.bedrock-runtime"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  security_group_ids  = [aws_security_group.bedrock.id]
  subnet_ids          = [aws_subnet.private_a.id, aws_subnet.private_b.id]

  tags = {
    Name = "${var.app_name}-${var.environment}-vpce-bedrock"
  }
}

# --- Interface Endpoint for Textract ---
resource "aws_security_group" "textract" {
  name        = "${var.app_name}-${var.environment}-textract-sg"
  description = "Security group for Textract Interface Endpoint"
  vpc_id      = aws_vpc.main.id

  # Allow inbound HTTPS traffic from Lambda SG
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }

  tags = {
    Name = "${var.app_name}-${var.environment}-textract-sg"
  }
}

resource "aws_vpc_endpoint" "textract" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.textract"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  security_group_ids  = [aws_security_group.textract.id]
  subnet_ids          = [aws_subnet.private_a.id, aws_subnet.private_b.id]

  tags = {
    Name = "${var.app_name}-${var.environment}-vpce-textract"
  }
}
# --- VPC Flow Logs Configuration (Best Practice) ---
resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  name              = "/aws/vpc-flow-logs/${aws_vpc.main.id}"
  retention_in_days = 14

  tags = {
    Name = "${var.app_name}-${var.environment}-vpc-flow-logs-group"
  }
}

resource "aws_iam_role" "vpc_flow_logs_role" {
  name = "${var.app_name}-${var.environment}-vpc-flow-logs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "vpc_flow_logs_policy" {
  name = "${var.app_name}-${var.environment}-vpc-flow-logs-policy"
  role = aws_iam_role.vpc_flow_logs_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

resource "aws_flow_log" "main" {
  iam_role_arn    = aws_iam_role.vpc_flow_logs_role.arn
  log_destination = aws_cloudwatch_log_group.vpc_flow_logs.arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.main.id

  tags = {
    Name = "${var.app_name}-${var.environment}-vpc-flow-log"
  }
}
