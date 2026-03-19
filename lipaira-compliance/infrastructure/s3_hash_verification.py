"""
A-04: Tamper-Evidence Hashing
Lambda function for S3 log batch verification
"""

import hashlib
import json
import boto3
from datetime import datetime


# Lambda function code for hash verification
LAMBDA_CODE = '''
import hashlib
import json
import boto3
import os
from datetime import datetime, timedelta

s3 = boto3.client('s3')
logs = boto3.client('logs')
sns = boto3.client('sns')

LOG_BUCKET = os.environ['LOG_BUCKET']
ALERT_TOPIC_ARN = os.environ.get('ALERT_TOPIC_ARN')


def lambda_handler(event, context):
    """Daily verification of log file integrity - A-04"""
    
    today = datetime.utcnow().date()
    prefix = f"logs/{today.isoformat()}/"
    
    response = s3.list_objects_v2(Bucket=LOG_BUCKET, Prefix=prefix)
    
    if 'Contents' not in response:
        print(f"No logs found for {today.isoformat()}")
        return {"status": "no_logs"}
    
    verification_results = []
    
    for obj in response['Contents']:
        key = obj['Key']
        obj_metadata = s3.head_object(Bucket=LOG_BUCKET, Key=key)
        stored_hash = obj_metadata.get('ObjectHash', '')
        
        if not stored_hash:
            verification_results.append({
                "key": key,
                "status": "MISSING_HASH"
            })
            continue
        
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
            verification_results.append({"key": key, "status": "VERIFIED"})
    
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
        sns.publish(
            TopicArn=ALERT_TOPIC_ARN,
            Subject="Log Hash Verification Failed",
            Message=f"ALERT: {report['failed']} files failed verification"
        )
    
    return report
'''


# CloudFormation for S3 with Object Lock
S3_OBJECT_LOCK_CFN = '''
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Lipaira Immutable Log Storage - A-03'

Resources:
  # Log bucket with Object Lock (COMPLIANCE mode - 7 years)
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

  # KMS Key for encryption - C-11
  LogKMSKey:
    Type: AWS::KMS::Key
    Properties:
      Description: 'Lipaira Log Encryption Key'
      EnableKeyRotation: true
      KeyPolicy:
        Version: '2012-10-17'
        Statement:
          - Sid: Enable Root
            Effect: Allow
            Principal:
              AWS: !Sub 'arn:aws:iam::${AWS::AccountId}:root'
            Action: kms:*
            Resource: '*'
          - Sid: Allow Logs Service
            Effect: Allow
            Principal:
              Service: logs.amazonaws.com
            Action:
              - kms:Encrypt
              - kms:Decrypt
              - kms:GenerateDataKey
            Resource: '*'

  # Break-glass role - C-13
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
            Statement:
              - Effect: Allow
                Action: s3:DeleteObject
                Resource: !Sub '${LogBucket.Arn}/*'
'''


# Hash utility for writing logs
def compute_log_hash(content: str) -> str:
    """Compute SHA-256 hash of log content"""
    return hashlib.sha256(content.encode()).hexdigest()