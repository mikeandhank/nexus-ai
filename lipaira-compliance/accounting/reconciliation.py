"""
B-06 to B-10: Accounting Data Warehouse & Reconciliation
B-11 to B-12: Chargeback Defence
"""

from datetime import datetime, timedelta
from typing import Optional
import json


# B-06: Financial Data Lake on S3
DATA_LAKE_SQL = '''
-- Create data lake S3 buckets
-- s3://lipaira-datalake/revenue/YYYY/MM/
-- s3://lipaira-datalake/cogs/YYYY/MM/
-- s3://lipaira-datalake/tax/YYYY/MM/
-- s3://lipaira-datalake/refunds/YYYY/MM/

-- Partition by date for Athena queries
-- Store as Parquet for efficient querying
'''


# B-07: Athena Reporting Layer
ATHENA_QUERIES = '''
-- Monthly Revenue by Type
CREATE OR REPLACE VIEW monthly_revenue AS
SELECT 
    DATE_TRUNC('month', timestamp) as month,
    event_type,
    SUM(amount_cents) as total_revenue_cents,
    COUNT(*) as transaction_count
FROM revenue_events
GROUP BY DATE_TRUNC('month', timestamp), event_type;

-- Monthly COGS
CREATE OR REPLACE VIEW monthly_cogs AS
SELECT 
    DATE_TRUNC('month', timestamp) as month,
    model,
    SUM(tokens_total) as total_tokens,
    SUM(cost_usd) as total_cost_usd
FROM cogs_events
GROUP BY DATE_TRUNC('month', timestamp), model;

-- Gross Margin
CREATE OR REPLACE VIEW gross_margin AS
SELECT 
    r.month,
    r.total_revenue_cents,
    c.total_cost_cents,
    r.total_revenue_cents - c.total_cost_cents as gross_margin_cents,
    ROUND(
        (r.total_revenue_cents - c.total_cost_cents)::numeric / r.total_revenue_cents * 100,
        2
    ) as margin_percent
FROM 
    (SELECT DATE_TRUNC('month', timestamp) as month, SUM(amount_cents) as total_revenue_cents FROM revenue_events GROUP BY 1) r
    JOIN
    (SELECT DATE_TRUNC('month', timestamp) as month, SUM(cost_usd * 100) as total_cost_cents FROM cogs_events GROUP BY 1) c
    ON r.month = c.month;
'''


# B-08: Monthly Close Automation Lambda
MONTHLY_CLOSE_LAMBDA = '''
import boto3
import json
from datetime import datetime

s3 = boto3.client('s3')
athena = boto3.client('athena')

DATALAKE_BUCKET = 'lipaira-datalake'

def lambda_handler(event, context):
    """B-08: Monthly close automation - runs 1st of each month"""
    
    today = datetime.utcnow()
    last_month = today.replace(day=1) - timedelta(days=1)
    month_str = last_month.strftime('%Y-%m')
    
    # Snapshot all financial ledgers
    snapshots = {
        'revenue': snapshot_table('revenue_events', month_str),
        'cogs': snapshot_table('cogs_events', month_str),
        'tax': snapshot_table('tax_collection', month_str),
        'refunds': snapshot_table('refunds_and_disputes', month_str)
    }
    
    # Generate monthly summary
    summary = generate_monthly_summary(month_str)
    
    # Write summary
    summary_key = f"monthly/{month_str}/summary.json"
    s3.put_object(
        Bucket=DATALAKE_BUCKET,
        Key=summary_key,
        Body=json.dumps(summary, indent=2),
        ContentType='application/json'
    )
    
    # Notify founder
    send_notification(summary)
    
    return {"status": "completed", "month": month_str, "summary": summary}


def snapshot_table(table_name: str, month_str: str):
    """Export table to Parquet in S3"""
    query = f"SELECT * FROM {table_name} WHERE DATE_TRUNC('month', timestamp) = '{month_str}'"
    # Execute Athena query and save to S3
    pass


def generate_monthly_summary(month_str: str) -> dict:
    """Generate monthly accounting summary"""
    return {
        "month": month_str,
        "total_revenue_cents": 0,
        "total_cogs_cents": 0,
        "gross_margin_cents": 0,
        "refund_rate": 0,
        "tax_collected_cents": 0,
        "generated_at": datetime.utcnow().isoformat()
    }
'''


# B-09: QuickBooks/Xero Export
ACCOUNTING_EXPORT = '''
import csv
import boto3
from io import StringIO

# B-09: Daily export for accounting software import
class AccountingExport:
    
    def export_revenue_to_qbo(self, start_date, end_date) -> str:
        """Export revenue for QuickBooks Online import"""
        # QBO CSV format
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'TransactionType', 'Amount', 'Account', 'Description'])
        
        # Query revenue events and format
        for event in revenue_events:
            writer.writerow([
                event['timestamp'][:10],
                'Payment',
                event['total_charged_cents'] / 100,
                'Revenue',
                f"Token credits - {event['customer_id']}"
            ])
        
        return output.getvalue()
    
    def export_cogs_to_qbo(self, start_date, end_date) -> str:
        """Export COGS for QuickBooks Online import"""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'TransactionType', 'Amount', 'Account', 'Description'])
        
        for event in cogs_events:
            writer.writerow([
                event['timestamp'][:10],
                'Expense',
                event['cost_usd'],
                'COGS - LLM API',
                f"{event['model']} - {event['customer_id']}"
            ])
        
        return output.getvalue()
    
    def save_to_s3(self, content: str, prefix: str):
        """Save export to S3 for bookkeeper"""
        s3_key = f"accounting/exports/{prefix}/{datetime.utcnow().date()}.csv"
        s3.put_object(Bucket='lipaira-reports', Key=s3_key, Body=content)
        return s3_key
'''


# B-10: Stripe → Accounting Sync Validation
STRIPE_SYNC_VALIDATION = '''
import boto3

def weekly_stripe_reconciliation():
    """B-10: Compare Stripe payouts vs revenue ledger"""
    
    stripe_client = boto3.client('stripe')  # or use stripe SDK
    
    # Get Stripe payouts
    stripe_payouts = stripe_client.list_payouts()['data']
    stripe_total = sum(p['amount'] for p in stripe_payouts)
    
    # Get revenue ledger total
    ledger_total = get_revenue_ledger_total()
    
    # Compare
    discrepancy = abs(stripe_total - ledger_total)
    
    if discrepancy > 100:  # $1.00 in cents
        alert_on_discrepancy(stripe_total, ledger_total, discrepancy)
    else:
        print(f"Reconciliation OK: difference ${discrepancy/100:.2f}")
    
    return {"stripe_total": stripe_total, "ledger_total": ledger_total, "discrepancy": discrepancy}


def alert_on_discrepancy(stripe, ledger, diff):
    """Alert if reconciliation fails"""
    sns.publish(
        TopicArn='arn:aws:sns:us-east-1:ACCOUNT:lipaira-alerts',
        Subject='STRIPE RECONCILIATION ALERT',
        Message=f'Stripe: ${stripe/100:.2f}, Ledger: ${ledger/100:.2f}, Diff: ${diff/100:.2f}'
    )
'''


# B-11: Dispute Evidence Package Generator
class DisputeEvidenceGenerator:
    """B-11: Auto-generate chargeback dispute evidence"""
    
    async def generate_evidence_package(self, stripe_dispute_id: str) -> dict:
        """Assemble dispute evidence for Stripe"""
        
        # Get original purchase record
        purchase = await get_original_purchase(stripe_dispute_id)
        
        # Get credit ledger showing consumption
        credit_ledger = await get_credit_ledger(purchase['customer_id'])
        
        # Get OpenRouter logs before dispute
        usage_logs = await get_openrouter_logs(
            purchase['customer_id'],
            start=purchase['timestamp'],
            end=purchase['timestamp'] + timedelta(days=30)
        )
        
        # Get ToS acceptance
        tos_acceptance = await get_tos_acceptance(purchase['customer_id'])
        
        return {
            "dispute_id": stripe_dispute_id,
            "purchase_record": purchase,
            "credit_ledger": credit_ledger,
            "usage_logs": usage_logs,
            "tos_acceptance": tos_acceptance,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def attach_to_stripe_dispute(self, evidence: dict):
        """Attach evidence package to Stripe dispute"""
        # Use Stripe API to upload evidence
        pass


# B-12: Consumed vs Unearned Credits Snapshot
class CreditSnapshot:
    """B-12: Snapshot at moment of refund/dispute"""
    
    async def snapshot_for_dispute(self, customer_id: str, dispute_id: str) -> dict:
        """Create immutable snapshot for dispute"""
        
        total_purchased = await self.get_total_purchased(customer_id)
        total_consumed = await self.get_total_consumed(customer_id)
        total_remaining = total_purchased - total_consumed
        
        snapshot = {
            "snapshot_id": f"snap-{dispute_id}",
            "customer_id": customer_id,
            "total_purchased": total_purchased,
            "total_consumed": total_consumed,
            "total_remaining": total_remaining,
            "unearned_value_cents": total_remaining * 100 / 1000,  # Assuming 1000 credits/$1
            "snapshot_timestamp": datetime.utcnow().isoformat(),
            "dispute_id": dispute_id
        }
        
        # Store immutably
        await self.store_snapshot(snapshot)
        
        return snapshot