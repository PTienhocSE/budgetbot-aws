resource "aws_backup_vault" "main" {
  name        = "${var.app_name}-${var.environment}-backup-vault"
  kms_key_arn = aws_kms_key.s3_key.arn
}

resource "aws_backup_plan" "daily" {
  name = "${var.app_name}-${var.environment}-daily-backup"

  rule {
    rule_name         = "daily-backup-rule"
    target_vault_name = aws_backup_vault.main.name
    schedule          = "cron(0 2 * * ? *)" # 2:00 AM UTC

    lifecycle {
      delete_after = 7 # Keep backups for 7 days to save costs
    }
  }
}

resource "aws_iam_role" "backup_role" {
  name = "${var.app_name}-${var.environment}-backup-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "backup.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "backup_role_policy" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
  role       = aws_iam_role.backup_role.name
}

resource "aws_backup_selection" "dynamodb_selection" {
  iam_role_arn = aws_iam_role.backup_role.arn
  name         = "${var.app_name}-${var.environment}-dynamodb-backup"
  plan_id      = aws_backup_plan.daily.id

  resources = [
    aws_dynamodb_table.transactions.arn
  ]
}
