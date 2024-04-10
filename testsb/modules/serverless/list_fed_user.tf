# IAM Role for list_fed_user Lambda Function
# -----------------------------------------
# This resource block defines an IAM role for the Lambda function named list_fed_user_lambda.

resource "aws_iam_role" "list_fed_user_lambda_role" {
  name = "list_fed_user_lambda_execution_role"  # Name of the IAM role
  
  # Policy allowing Lambda service to assume the role
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })

  # Attach required managed policies to the role
  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    "arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess",
    "arn:aws:iam::aws:policy/AWSLambda_FullAccess",
    "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
  ]
}


# Archive Lambda function code
# -----------------------------
# This data source archives the Lambda function code located in the "src" directory.

data "archive_file" "list_fed_user_lambda_zip" {
  type        = "zip"
  source_dir  = "src"
  output_path = "${path.module}/list_fed_user_lambda.zip"
}


# Lambda Function - list_fed_user
# ------------------------------
# This resource block defines the Lambda function named list_fed_user_lambda.

resource "aws_lambda_function" "list_fed_user_lambda" {
  filename      = data.archive_file.list_fed_user_lambda_zip.output_path  # Path to the Lambda function code zip archive
  function_name = "list_fed_user_lambda"  # Name of the Lambda function
  role          = aws_iam_role.list_fed_user_lambda_role.arn  # IAM role ARN attached to the Lambda function
  handler       = "list_fed_user.lambda_handler"  # Entry point to the Lambda function
  runtime       = "python3.8"  # Runtime environment for the Lambda function
  timeout = 30

# Add tags for better organization and management
  tags = {

    Owner   = var.Owner
    Creator = var.Creator
    Project = var.Project
  }

}

# # Grant permission to EventBridge to invoke the Lambda function
# # -------------------------------------------------------------
# resource "aws_lambda_permission" "allow_eventbridge_invoke" {
#   statement_id  = "AllowExecutionFromEventBridge"
#   action        = "lambda:InvokeFunction"
#   function_name = aws_lambda_function.list_fed_user_lambda.function_name
#   principal     = "events.amazonaws.com"
#   source_arn    = aws_cloudwatch_event_rule.federated_cron_job.arn
# }

