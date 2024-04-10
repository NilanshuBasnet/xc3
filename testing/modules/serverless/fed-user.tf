data "archive_file" "fed_user_resource_zip" {
  type        = "zip"
  source_dir = "src"
  output_path = "${path.module}/fed_user_resource.zip"

}


data "archive_file" "list-fed-user_zip" {
  type        = "zip"
  source_dir = "src"
  output_path = "${path.module}/list-fed-user.zip"

}


# Creating Inline policy
resource "aws_iam_role_policy" "fed-user-policy" {
  name = "${var.namespace}-fed-user-policy"
  role = aws_iam_role.fed-user_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid = "CostExplorer"
        Action = [
          "ce:GetCostAndUsage",
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DetachNetworkInterface",
          "ec2:AttachNetworkInterface",
          "ec2:DeleteNetworkInterface",
          "SNS:Publish"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}



# Creating IAM Role for Lambda functions
resource "aws_iam_role" "fed-user_role" {
  name = "${var.namespace}-fed-user_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  managed_policy_arns = [
    "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
    "arn:aws:iam::aws:policy/ResourceGroupsandTagEditorReadOnlyAccess",
    "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole",
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  ]

  #tags = merge(local.tags, tomap({ "Name" = "${var.namespace}-fed-user_role" }))
}

resource "aws_lambda_function" "fed_user_resource" {
  #ts:skip=AC_AWS_0485 We are aware of the risk and choose to skip this rule
  #ts:skip=AC_AWS_0483 We are aware of the risk and choose to skip this rule
  #ts:skip=AC_AWS_0484 We are aware of the risk and choose to skip this rule
  function_name = "${var.namespace}-fed_user_resource"
  role          = aws_iam_role.fed-user_role.arn
  runtime       = "python3.9"
  handler       = "fed_user_resource.lambda_handler"
  filename      =  data.archive_file.fed_user_resource_zip.output_path
  environment {
    variables = {
      prometheus_ip = "${var.prometheus_ip}:9091"
      region_names_path = "/${var.namespace}/region_names"
      sns_topic     = var.sns_topic_arn
      bucket_name = var.s3_xc3_bucket.bucket
    }
  }
  memory_size = var.memory_size
  timeout     = var.timeout
  layers      = [var.prometheus_layer]
  depends_on = [
    aws_lambda_function.list_fed_user
  ]
  #tags = merge(local.tags, tomap({ "Name" = "${var.namespace}-fed_user_resource" }))

}





resource "aws_lambda_function" "list_fed_user" {
  #ts:skip=AC_AWS_0484 We are aware of the risk and choose to skip this rule
  #ts:skip=AC_AWS_0485 We are aware of the risk and choose to skip this rule
  #ts:skip=AC_AWS_0483 We are aware of the risk and choose to skip this rule
  function_name = "${var.namespace}-list_fed_users"
  role          = aws_iam_role.fed-user_role.arn
  runtime       = "python3.9"
  handler       = "list_fed_user.lambda_handler"
  filename      = data.archive_file.list-fed-user_zip.output_path
  environment {
    variables = {
      prometheus_ip = "${var.prometheus_ip}:9091"
      REGION        = var.region
      sns_topic     = var.sns_topic_arn
      bucket_name = var.s3_xc3_bucket.bucket

    }
  }
  memory_size = var.memory_size
  timeout     = var.timeout
  layers      = [var.prometheus_layer]
  
 # tags = merge(local.tags, tomap({ "Name" = "${var.namespace}-list_fed_user" }))
}



resource "terraform_data" "delete_fed_user_zip_file" {
  triggers_replace = [aws_lambda_function.list_fed_user.arn]
  provisioner "local-exec" {
    command = "rm -r ${data.archive_file.list-fed-user_zip.output_path}"
  }
}

resource "aws_s3_bucket_notification" "list_fed_user_trigger" {
  bucket = var.s3_xc3_bucket.id
  lambda_function {
    lambda_function_arn = aws_lambda_function.list_fed_user.arn
    filter_prefix       = "iam-user/"
    events              = ["s3:ObjectCreated:Put"]
    filter_suffix       = "resources.json.gz"
  }
}


resource "aws_lambda_permission" "allow_bucket_for_trigger" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.list_fed_user.arn
  principal     = "s3.amazonaws.com"
  source_arn    = var.s3_xc3_bucket.arn
}