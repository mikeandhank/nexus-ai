"""
A-04: Tamper-Evidence Hashing
Lambda function for S3 log batch verification
"""

import hashlib
import json
import boto3
from datetime import datetime, timedelta


# Lambda function code
LAMBDA_HASH_VERIFICATION = '''
"""
A-04: Daily hash verification Lambda
Validates SHA-256 hashes of log batches in S3
"""

import boto3
import hashlib
import json
import os
from datetime import datetime, timedelta

s3 = boto3.client('s3')
logs = boto3.client('logs')
sns = boto3.client('sns')

LOG_BUCKET = os.environ['LOG_BUCKET']
ALERT_TOPIC_ARN = os.environ.get('ALERT_TOPIC_ARN')


def lambda_handler(event, context):
    """Daily verification of log file integrity"""
    
    today = datetime.utcnow().date()
    prefix = f"logs/{today.isoformat()}/"
    
    # List all log files
    response = s3.list_objects_v2(
        Bucket=LOG_BUCKET,
        Prefix=prefix
    )
    
    if 'Contents' not in response:
        print(f"No logs found for {today.isoformat()}")
        return {"status": "no_logs"}
    
    verification_results = []
    
    for obj in response['Contents']:
        key = obj['Key']
        
        # Get stored hash from metadata
        obj_metadata = s3.head_object(Bucket=LOG_BUCKET, Key=key)
        stored_hash = obj_metadata.get('ObjectHash', '')
        
        if not stored_hash:
            verification_results.append({
                "key": key,
                "status": "MISSING_HASH",
                "error": "No hash in metadata"
            })
            continue
        
        # Download and compute actual hash
        obj_body = s3.get_object(Bucket=LOG_BUCKET, Key=key)
        content = obj_body['Body'].read()
        actual_hash = hashlib.sha256(content).hexdigest()
        
        if actual_hash != stored_hash:
            verification_results.append({
                "key": key,
                "status": "HASH_MISMATCH",
                "stored": stored_hash,
                "actual": actual_hash
            })
        else:
            verification_results.append({
                "key": key,
                "status": "VERIFIED"
            })
    
    # Write verification report
    report_key = f"verification/{today.isoformat()}/report.json"
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "date": today.isoformat(),
        "total_files": len(verification_results),
        "verified": sum(1 for r in verification_results if r['status'] == 'VERIFIED'),
        "failed": sum(1 for r in verification_results if r['status'] != 'VERIFIED'),
        "results": verification_results
    }
    
    s3.put_object(
        Bucket=LOG_BUCKET,
        Key=report_key,
        Body=json.dumps(report, indent=2),
        ContentType="application/json"
    )
    
    # Alert on failures
    if report['failed'] > 0 and ALERT_TOPIC_ARN:
        alert_msg = f"🚨 LOG INTEGRITY ALERT\n\nDate: {today.isoformat()}\nFailed: {report['failed']}/{report['total_files']}"
        sns.publish(
            TopicArn=ALERT_TOPIC_ARN,
            Subject="Log Hash Verification Failed",
            Message=alert_msg
        )
    
    return report
'''

# CloudFormation template for S3 with Object Lock
S3_OBJECT_LOCK_CFN = '''
# A-03: S3 Object Lock Configuration (COMPLIANCE mode)
# Run this once - cannot be disabled after enabling

AWSTemplateFormatVersion: '2010-09-09'
Description: 'Lipaira Immutable Log Storage'

Resources:
  # Enable Object Lock at account level
  EnableObjectLock:
    Type: AWS::S3::AccountPublicAccessBlock
    Properties:
      AccountId: !Ref AWS::AccountId
      BlockPublicAcls: true
      BlockPublicPolicy: true
      IgnorePublicAcls: true
      RestrictPublicBuckets: true

  # Log bucket with Object Lock
  LogBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: lipaira-logs
      ObjectLockEnabled: true
      ObjectLockRule:
        DefaultRetention:
          Mode: COMPLIANCE
          Days: 2555  # 7 years
      VersioningConfiguration:
        Status: Enabled
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: aws:kms
              KMSMasterKeyId: !Ref LogKMSKey
      
  # Prevent accidental deletion (except break-glass)
  LogBucketPolicy:
    Type: AWS::S3::BucketPolicy
    Properties:
      Bucket: !Ref LogBucket
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Sid: DenyDelete
            Effect: Deny
            Principal: '*'
            Action: s3:DeleteObject
            Resource: !Sub '${LogBucket.Arn}/*'
            Condition:
              StringNotEquals:
                aws:PrincipalARN: !Sub 'arn:aws:iam::${AWS::AccountId}:role/break-glass'

  # KMS Key for encryption
  LogKMSKey:
    Type: AWS::KMS::Key
    Properties:
      Description: 'Lipaira Log Encryption Key'
      KeyPolicy:
        Version: '2012-10-17'
        Statement:
          - Sid: Enable IAM User Permissions
            Effect: Allow
            Principal:
              AWS: !Sub 'arn:aws:iam::${AWS::AccountId}:root'
            Action: kms:*
            Resource: '*'
          - Sid: Allow Log Service Usage
            Effect: Allow
            Principal:
              Service: logs.amazonaws.com
            Action:
              - kms:Encrypt
              - kms:Decrypt
              - kms:GenerateDataKey
            Resource: '*'

  # Break-glass role (emergency access only)
  BreakGlassRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: lipaira-break-glass
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              AWS: !Sub 'arn:aws:iam::${AWS::AccountId}:user/founder'
            Action: sts:AssumeRole
      Policies:
        - PolicyName: BreakGlassS3
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - s3:DeleteObject
                Resource: !Sub '${LogBucket.Arn}/*'
'''

# Hash computation when writing logs
LOG_WRITER_HASH = '''
import hashlib
import boto3

s3 = boto3.client('s3')

def write_log_batch(bucket: str, date: str, logs: list):
    """Write log batch with SHA-256 hash"""
    
    content = "\\n".join(logs)
    content_bytes = content.encode()
    
    # Compute hash
    content_hash = hashlib.sha256(content_bytes).hexdigest()
    
    key = f"logs/{date}/{content_hash}.jsonl"
    
    # Upload with hash in metadata
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=content_bytes,
        ContentType="application/jsonl",
        Metadata={
            "content-sha256": content_hash,
            "record-count": str(len(logs)),
            "created-at": datetime.utcnow().isoformat()
        }
    )
    
    return key
'''
