data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../lambda" 
  output_path = "${path.module}/lambda_function.zip"
}

resource "aws_lambda_function" "nba_data_fetcher" {
  function_name = var.function_name
  role          = var.lambda_role_arn

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  runtime = "python3.11"
  handler = "lambda_function.lambda_handler"

  timeout     = 30
  memory_size = 256

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [var.lambda_security_group_id]
  }
  environment {
    variables = {
      DB_HOST                = var.db_host
      NBA_API_KEY_SECRET_ARN = var.nba_api_key_secret_arn
      DB_PASSWORD_SECRET_ARN = var.db_password_secret_arn
    }
  }
}

resource "aws_cloudwatch_event_rule" "nba_fetch_schedule" {
  name                = "${var.function_name}-schedule"
  schedule_expression = var.schedule_expression
}

resource "aws_cloudwatch_event_target" "nba_fetch_target" {
  rule = aws_cloudwatch_event_rule.nba_fetch_schedule.name
  arn  = aws_lambda_function.nba_data_fetcher.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.nba_data_fetcher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.nba_fetch_schedule.arn
}
