# Install dependencies for the Lambda Linux x86_64 runtime into lambda/package
# and copy the handler alongside them. Re-runs when requirements.txt or
# lambda_function.py change, or when lambda/package/ is absent (e.g. a fresh CI checkout).
resource "null_resource" "lambda_dependencies" {
  triggers = {
    requirements_hash = filesha256("${path.root}/../lambda/requirements.txt")
    source_hash       = filesha256("${path.root}/../lambda/lambda_function.py")
    package_present   = fileexists("${path.root}/../lambda/package/lambda_function.py") ? "present" : timestamp()
  }

  provisioner "local-exec" {
    working_dir = "${path.root}/.."
    command     = <<-EOT
      set -e
      rm -rf lambda/package
      mkdir -p lambda/package
      pip install -r lambda/requirements.txt -t lambda/package --platform manylinux2014_x86_64 --implementation cp --python-version 3.11 --only-binary=:all:
      cp lambda/lambda_function.py lambda/package/
    EOT
  }
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../lambda/package"
  output_path = "${path.module}/lambda_function.zip"

  depends_on = [null_resource.lambda_dependencies]
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
      DB_USER                = var.db_username
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
