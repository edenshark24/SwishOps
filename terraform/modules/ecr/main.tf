resource "aws_ecr_repository" "repos" {
  count = length(var.repository_names)
  name  = "${var.project_name}-${var.environment}-${var.repository_names[count.index]}"

  image_scanning_configuration {
    scan_on_push = true
  }
}
