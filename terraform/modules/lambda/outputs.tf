output "function_arn" {
  description = "arn of lambda"
  value       = aws_lambda_function.nba_data_fetcher.arn
}

output "function_name" {
  description = "name of lambda"
  value = aws_lambda_function.nba_data_fetcher.function_name

}

