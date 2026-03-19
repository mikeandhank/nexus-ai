"""
C-13: Least Privilege IAM Policies
Each service gets dedicated IAM role with minimal permissions
"""

# IAM Policy Documents
IAM_POLICIES = {
    "app_server": {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "DatabaseAccess",
                "Effect": "Allow",
                "Action": [
                    "rds-db:connect"
                ],
                "Resource": "arn:aws:rds-db:us-east-1:ACCOUNT:dbuser:*/lipaira_app"
            },
            {
                "Sid": "SecretsManager",
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:GetSecretValue"
                ],
                "Resource": [
                    "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:lipaira/*"
                ]
            },
            {
                "Sid": "S3AppData",
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject"
                ],
                "Resource": "arn:aws:s3:::lipaira-app-data/*"
            },
            {
                "Sid": "S3Logs",
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject"
                ],
                "Resource": "arn:aws:s3:::lipaira-logs/*"
            },
            {
                "Sid": "KMS",
                "Effect": "Allow",
                "Action": [
                    "kms:Encrypt",
                    "kms:Decrypt",
                    "kms:GenerateDataKey"
                ],
                "Resource": "arn:aws:kms:us-east-1:ACCOUNT:key/*"
            },
            {
                "Sid": "CloudWatchLogs",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws:logs:us-east-1:ACCOUNT:log-group:/lipaira/*"
            },
            {
                "Sid": "SQS",
                "Effect": "Allow",
                "Action": [
                    "sqs:SendMessage",
                    "sqs:ReceiveMessage",
                    "sqs:DeleteMessage"
                ],
                "Resource": "arn:aws:sqs:us-east-1:ACCOUNT:lipaira-*"
            }
        ]
    },
    
    "lambda_processor": {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "DynamoDB",
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:Query",
                    "dynamodb:Scan"
                ],
                "Resource": "arn:aws:dynamodb:us-east-1:ACCOUNT:table/lipaira-*"
            },
            {
                "Sid": "S3Read",
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject"
                ],
                "Resource": "arn:aws:s3:::lipaira-datalake/*"
            },
            {
                "Sid": "S3Write",
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject"
                ],
                "Resource": "arn:aws:s3:::lipaira-reports/*"
            },
            {
                "Sid": "CloudWatch",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws:logs:us-east-1:ACCOUNT:log-group:/lipaira/lambda/*"
            }
        ]
    },
    
    "reconciliation_job": {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "DatabaseRead",
                "Effect": "Allow",
                "Action": [
                    "rds-db:connect"
                ],
                "Resource": "arn:aws:rds-db:us-east-1:ACCOUNT:dbuser:*/lipaira_readonly"
            },
            {
                "Sid": "StripeRead",
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:GetSecretValue"
                ],
                "Resource": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:lipaira/stripe*"
            },
            {
                "Sid": "S3WriteReports",
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject"
                ],
                "Resource": "arn:aws:s3:::lipaira-reports/*"
            },
            {
                "Sid": "SNSAlerts",
                "Effect": "Allow",
                "Action": [
                    "sns:Publish"
                ],
                "Resource": "arn:aws:sns:us-east-1:ACCOUNT:lipaira-alerts"
            }
        ]
    },
    
    "break_glass": {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllS3",
                "Effect": "Allow",
                "Action": "s3:*",
                "Resource": "arn:aws:s3:::*"
            },
            {
                "Sid": "AllKMS",
                "Effect": "Allow",
                "Action": "kms:*",
                "Resource": "*"
            },
            {
                "Sid": "AllIAM",
                "Effect": "Allow",
                "Action": "iam:*",
                "Resource": "*"
            }
        ],
        "Condition": {
            "Bool": {
                "aws:MultiFactorAuthPresent": "true"
            }
        }
    }
}

# IAM Role definitions
IAM_ROLES = [
    {
        "name": "lipaira-app-server",
        "description": "Main application server role",
        "policies": ["app_server"],
        "trusted_entity": "ec2.amazonaws.com"
    },
    {
        "name": "lipaira-lambda-processor",
        "description": "Lambda function execution role",
        "policies": ["lambda_processor"],
        "trusted_entity": "lambda.amazonaws.com"
    },
    {
        "name": "lipaira-reconciliation",
        "description": "Daily reconciliation job role",
        "policies": ["reconciliation_job"],
        "trusted_entity": "scheduler.amazonaws.com"  # EventBridge
    },
    {
        "name": "lipaira-break-glass",
        "description": "Emergency access only - requires MFA",
        "policies": ["break_glass"],
        "trusted_entity": "iam.amazonaws.com"
    }
]


# Encryption Configuration
ENCRYPTION_CONFIG = '''
# C-11: Encryption at Rest - KMS Key Policy

AWSTemplateFormatVersion: '2010-09-09'
Description: 'Lipaira KMS Encryption Keys'

Resources:
  # Master Key for Financial Data
  FinancialKMSKey:
    Type: AWS::KMS::Key
    Properties:
      Description: 'Lipaira Financial Data Encryption'
      EnableKeyRotation: true
      KeyPolicy:
        Version: '2012-10-17'
        Statement:
          - Sid: Enable IAM User Permissions
            Effect: Allow
            Principal:
              AWS: !Sub 'arn:aws:iam::${AWS::AccountId}:root'
            Action: kms:*
            Resource: '*'
          - Sid: Allow Use By Services
            Effect: Allow
            Principal:
              Service:
                - rds.amazonaws.com
                - dynamodb.amazonaws.com
                - s3.amazonaws.com
            Action:
              - kms:Encrypt
              - kms:Decrypt
              - kms:GenerateDataKey
              - kms:CreateGrant
            Resource: '*'
            Condition:
              Bool:
                kms:GrantIsForAWSResource: true

  # Key for PII Data
  PIIKMSKey:
    Type: AWS::KMS::Key
    Properties:
      Description: 'Lipaira PII Encryption'
      EnableKeyRotation: true
      KeyPolicy:
        Version: '2012-10-17'
        Statement:
          - Sid: Enable IAM User Permissions
            Effect: Allow
            Principal:
              AWS: !Sub 'arn:aws:iam::${AWS::AccountId}:root'
            Action: kms:*
            Resource: '*'
          - Sid: Allow App Server Use
            Effect: Allow
            Principal:
              AWS: !Sub 'arn:aws:iam::${AWS::AccountId}:role/lipaira-app-server'
            Action:
              - kms:Encrypt
              - kms:Decrypt
              - kms:GenerateDataKey
            Resource: '*'

# C-12: TLS Configuration (ALB)
ALB_TLS_CONFIGURATION:
  # Use AWS ACM for certificates
  # Enforce TLS 1.2 minimum, prefer 1.3
  # Add HSTS headers
  
  HSTSHeaders: |
    Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
    X-Content-Type-Options: nosniff
    X-Frame-Options: DENY
    X-XSS-Protection: 1; mode=block
    
  ListenerRules:
    - Protocol: TLS
      SslPolicy: ELBSecurityPolicy-TLS13-1-2-2021
      Certificates:
        - CertificateArn: !Ref ACMCertificate
      DefaultActions:
        - Type: forward
          TargetGroupArn: !Ref AppTargetGroup
'''
