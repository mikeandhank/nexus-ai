"""
A-06: Real-Time Alerting
CloudWatch Metric Filters and Alarms
"""

# CloudFormation for CloudWatch Alerts
CLOUDWATCH_ALERMS_CFN = '''
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Lipaira CloudWatch Alerts - A-06'

Resources:
  # SNS Topic for alerts
  AlertTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: lipaira-alerts
      Subscription:
        - Protocol: email
          Endpoint: !Ref FounderEmail

  # A-06: Failed Authentication Alert
  FailedAuthAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: lipaira-failed-auth
      AlarmDescription: 'Alert on >5 failed auth attempts in 60s'
      MetricName: FailedAuthCount
      Namespace: Lipaira/Auth
      Statistic: Sum
      Period: 60
      EvaluationPeriods: 1
      Threshold: 5
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref AlertTopic

  # A-06: IAM Policy Change Alert
  IAMChangeAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: lipaira-iam-change
      AlarmDescription: 'Alert on IAM policy changes'
      MetricName: IAMPolicyChanges
      Namespace: AWS/IAM
      Statistic: Sum
      Period: 300
      EvaluationPeriods: 1
      Threshold: 0
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref AlertTopic

  # A-06: Root Account Usage Alert
  RootUsageAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: lipaira-root-usage
      AlarmDescription: 'Alert on root account usage'
      MetricName: RootAccountUsage
      Namespace: Lipaira/Admin
      Statistic: Sum
      Period: 60
      EvaluationPeriods: 1
      Threshold: 0
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref AlertTopic

  # A-06: S3 Bucket Policy Change Alert
  S3PolicyChangeAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: lipaira-s3-policy-change
      AlarmDescription: 'Alert on S3 bucket policy changes'
      MetricName: BucketPolicyChanges
      Namespace: AWS/S3
      Statistic: Sum
      Period: 300
      EvaluationPeriods: 1
      Threshold: 0
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref AlertTopic

  # A-06: Log Deletion Alert
  LogDeletionAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: lipaira-log-deletion
      AlarmDescription: 'Alert on any log resource deletion'
      MetricName: LogGroupDeletion
      Namespace: AWS/Logs
      Statistic: Sum
      Period: 60
      EvaluationPeriods: 1
      Threshold: 0
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref AlertTopic

Parameters:
  FounderEmail:
    Type: String
    Default: founder@lipaira.cloud
'''


# Python code to emit custom metrics
class CloudWatchMetrics:
    """A-06: Emit custom CloudWatch metrics"""
    
    def __init__(self):
        self.client = boto3.client('cloudwatch')
    
    def put_auth_metric(self, success: bool):
        """Emit authentication metric"""
        self.client.put_metric_data(
            Namespace='Lipaira/Auth',
            MetricData=[{
                'MetricName': 'AuthAttempt',
                'Value': 1,
                'Timestamp': datetime.utcnow(),
                'Dimensions': [{'Name': 'Outcome', 'Value': 'success' if success else 'failure'}]
            }]
        )
    
    def put_api_metric(self, latency_ms: int, status_code: int):
        """Emit API performance metric"""
        self.client.put_metric_data(
            Namespace='Lipaira/API',
            MetricData=[
                {'MetricName': 'Latency', 'Value': latency_ms, 'Unit': 'Milliseconds', 'Timestamp': datetime.utcnow()},
                {'MetricName': 'RequestCount', 'Value': 1, 'Timestamp': datetime.utcnow(), 
                 'Dimensions': [{'Name': 'StatusCode', 'Value': str(status_code)}]}
            ]
        )