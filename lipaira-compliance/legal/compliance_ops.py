"""
C-14 to C-18: Security & Operational Compliance
- Vulnerability scanning
- Incident response
- Data retention enforcement
- Third-party DPA registry
"""

from datetime import datetime, timedelta
from typing import Optional


# C-14: Vulnerability Scanning Pipeline
VULNERABILITY_SCANNING = '''
# C-14: CI/CD Pipeline Integration
# GitHub Actions workflow for security scanning

name: Security Scan
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  vulnerability_scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      # Dependency scanning
      - name: NPM Audit
        run: npm audit --production --audit-level=high || true
        
      - name: Python Safety
        run: pip install safety && safety check -r requirements.txt || true
      
      # Container scanning
      - name: Trivy Scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'image'
          image-ref: 'lipaira:latest'
          severity: 'CRITICAL,HIGH'
      
      # SAST
      - name: Semgrep
        uses: returntocorp/semgrep-action@v1
      
      # Block on critical vulnerabilities
      - name: Block on Critical
        if: steps.trivy.outcome == 'failure'
        run: |
          echo "Critical vulnerabilities found - blocking deployment"
          exit 1
'''

# C-15: Incident Response Runbook
INCIDENT_RESPONSE = '''
# C-15: Incident Response Runbook

## Data Breach Response (72-hour GDPR window)

### Immediate Actions (0-1 hour)
1. Activate incident response team
2. Isolate affected systems
3. Preserve evidence (logs, snapshots)
4. Document timeline

### Assessment (1-4 hours)
1. Determine scope (what data, how many customers)
2. Assess if breach requires notification
3. Calculate 72-hour deadline

### Notification (within 72 hours)
1. Notify GDPR supervisory authority
2. Notify affected customers if high risk
3. Document all actions taken

### Technical Pre-conditions
- Kill-switch to disable all API keys
- Procedure to revoke Stripe webhooks
- Customer notification pipeline ready

## Kill Switch
POST /admin/kill-switch { "reason": "security_incident" }
- Revokes all active API keys
- Disables new signups
- Sends alert to on-call
'''


# C-16: GDPR Breach Detection Pipeline
BREACH_DETECTION = '''
import boto3
from datetime import datetime, timedelta

cloudwatch = boto3.client('cloudwatch')

# C-16: CloudWatch alarms for breach detection
BREACH_DETECTION_ALARMS = {
    'unusual_s3_egress': {
        'MetricName': 'S3BytesUploaded',
        'Threshold': 1000000000,  # 1GB
        'Period': 300,
        'EvaluationPeriods': 1
    },
    'bulk_database_reads': {
        'MetricName': 'DatabaseRowsRead',
        'Threshold': 100000,
        'Period': 300,
        'EvaluationPeriods': 1
    },
    'unexpected_iam_assumption': {
        'MetricName': 'IAMRoleAssumptions',
        'Threshold': 100,
        'Period': 60,
        'EvaluationPeriods': 1
    }
}


def check_breach_indicators():
    """C-16: Check for potential breach indicators"""
    
    for alarm_name, config in BREACH_DETECTION_ALARMS.items():
        response = cloudwatch.get_metric_statistics(
            Namespace='Lipaira',
            MetricName=config['MetricName'],
            StartTime=datetime.utcnow() - timedelta(minutes=10),
            EndTime=datetime.utcnow(),
            Period=config['Period'],
            Statistics=['Sum']
        )
        
        if response['Datapoints']:
            current_value = response['Datapoints'][0]['Sum']
            if current_value > config['Threshold']:
                create_incident_ticket(alarm_name, current_value)
                notify_founder(alarm_name, current_value)
                draft_breach_notification(alarm_name, current_value)


def draft_breach_notification(indicator: str, value: float):
    """C-16: Draft GDPR breach notification (ready to send)"""
    
    template = {
        "to": "privacy@lipaira.cloud",
        "subject": f"DRAFT: Potential Data Breach - {indicator}",
        "body": f"""
        Potential breach indicator detected:
        - Indicator: {indicator}
        - Value: {value}
        - Time: {datetime.utcnow().isoformat()}
        
        This is an automated draft for supervisory authority notification.
        Complete investigation before sending.
        
        GDPR Article 33: Notification within 72 hours.
        """
    }
    
    # Store draft for human review
    save_draft_notification(template)
'''


# C-17: Data Retention Enforcement
RETENTION_ENFORCEMENT = '''
import boto3
from datetime import datetime, timedelta

# C-17: Weekly Lambda to enforce retention policies
def lambda_handler(event, context):
    """C-17: Enforce data retention policies"""
    
    policies = {
        'access_logs': {'retention_days': 365, 'action': 'pseudonymize'},
        'session_data': {'retention_days': 90, 'action': 'delete'},
        'api_logs': {'retention_days': 2555, 'action': 'archive'},  # 7 years
        'customer_pii': {'retention_days': None, 'action': 'retain'}  # Legal obligation
    }
    
    enforcement_log = []
    
    for table, policy in policies.items():
        if policy['retention_days']:
            cutoff = datetime.utcnow() - timedelta(days=policy['retention_days'])
            processed = apply_retention_policy(table, cutoff, policy['action'])
            enforcement_log.append({
                'table': table,
                'cutoff': cutoff.isoformat(),
                'action': policy['action'],
                'records_processed': processed
            })
    
    # Write enforcement log
    write_enforcement_log(enforcement_log)
    
    return {'status': 'completed', 'processed': len(enforcement_log)}


def apply_retention_policy(table: str, cutoff, action: str) -> int:
    """Apply retention policy to table"""
    
    if action == 'delete':
        # Hard delete (after retention period)
        return delete_old_records(table, cutoff)
    
    elif action == 'pseudonymize':
        # Replace PII, keep for audit
        return pseudonymize_old_records(table, cutoff)
    
    elif action == 'archive':
        # Move to cold storage (S3 Glacier)
        return archive_to_glacier(table, cutoff)
    
    return 0


# C-17: Retention enforcement SQL
RETENTION_SQL = '''
-- Pseudonymize old access logs (keep IP hashed after 1 year)
UPDATE access_logs
SET 
    ip_address = encode(sha256((ip_address || '2025')::bytea), 'hex'),
    user_agent = '[REDACTED]'
WHERE timestamp < NOW() - INTERVAL '1 year'
AND ip_address IS NOT NULL;

-- Delete old session data (90 days)
DELETE FROM sessions WHERE last_activity < NOW() - INTERVAL '90 days';

-- Archive old logs to S3 (for 7-year requirement)
INSERT INTO log_archive (log_data, archived_at)
SELECT log_data, NOW() FROM logs WHERE timestamp < NOW() - INTERVAL '7 years';
DELETE FROM logs WHERE timestamp < NOW() - INTERVAL '7 years';
'''


# C-18: Third-Party DPA Registry
DPA_REGISTRY = '''
# C-18: Machine-readable DPA registry (JSON)

{
  "version": "1.0",
  "last_updated": "2026-03-19",
  "processors": [
    {
      "name": "Stripe",
      "description": "Payment processing",
      "data_categories": ["payment", "billing", "transactions"],
      "legal_basis": "contract",
      "dpa_status": "signed",
      "dpa_url": "https://stripe.com/legal",
      "subprocessors": ["Paymentez", "FastSpring"]
    },
    {
      "name": "OpenRouter",
      "description": "LLM API routing",
      "data_categories": ["prompts", "responses", "usage_metrics"],
      "legal_basis": "legitimate_interest",
      "dpa_status": "pending",
      "dpa_url": null
    },
    {
      "name": "AWS",
      "description": "Cloud infrastructure",
      "data_categories": ["all"],
      "legal_basis": "legitimate_interest",
      "dpa_status": "signed",
      "dpa_url": "https://aws.amazon.com/compliance/data-processing-agreement",
      "subprocessors": []
    }
  ]
}
'''

# DPA Compliance Check
class DPACompliance:
    """C-18: Track DPA status"""
    
    def get_pending_dp_as(self) -> list:
        """Get processors without signed DPA"""
        
        registry = load_dpa_registry()
        return [p for p in registry['processors'] if p['dpa_status'] != 'signed']
    
    def alert_on_missing_dpa(self):
        """Alert if any critical processor missing DPA"""
        
        pending = self.get_pending_dp_as()
        if pending:
            send_alert(
                f"Missing DPAs for: {', '.join(p['name'] for p in pending)}"
            )
    
    def require_dpa_before_use(self, processor_name: str) -> bool:
        """Block integration if no DPA"""
        
        registry = load_dpa_registry()
        processor = next((p for p in registry['processors'] if p['name'] == processor_name), None)
        
        if not processor or processor['dpa_status'] != 'signed':
            raise Exception(f"Cannot use {processor_name} - DPA required")
        
        return True
'''