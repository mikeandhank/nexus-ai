"""
UUID Migration Helper
=====================
Convert TEXT primary keys to UUID v4
"""
import uuid
import psycopg2
from typing import List, Dict


def generate_uuid() -> str:
    """Generate a new UUID v4"""
    return str(uuid.uuid4())


def create_uuid_columns(db_url: str) -> List[str]:
    """
    Add UUID columns to all tables as primary keys
    Returns list of migration steps taken
    """
    migrations = []
    
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # Tables to migrate
    tables = [
        'users', 'conversations', 'messages', 'agents', 
        'api_usage', 'api_keys', 'audit_log', 'kernel_agents',
        'kernel_events', 'kernel_ipc', 'user_balances', 'api_reloads'
    ]
    
    for table in tables:
        try:
            # Check if id column exists
            cursor.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table}' AND column_name = 'id'
            """)
            
            if cursor.fetchone():
                # Add UUID column
                cursor.execute(f"""
                    ALTER TABLE {table} 
                    ADD COLUMN IF NOT EXISTS id UUID PRIMARY KEY DEFAULT gen_random_uuid()
                """)
                migrations.append(f"Added UUID 'id' column to {table}")
            
        except Exception as e:
            migrations.append(f"Error on {table}: {e}")
    
    conn.commit()
    conn.close()
    
    return migrations


def backfill_uuid_ids(db_url: str) -> Dict:
    """
    Backfill missing UUIDs where needed
    """
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    results = {}
    
    # Tables with TEXT primary keys to convert
    tables_with_text_ids = [
        ('users', 'user_id'),
        ('conversations', 'conversation_id'),
        ('messages', 'message_id'),
        ('agents', 'agent_id'),
        ('api_usage', 'usage_id'),
        ('api_keys', 'key_id'),
        ('audit_log', 'log_id'),
        ('kernel_agents', 'agent_id'),
        ('kernel_events', 'event_id'),
        ('kernel_ipc', 'message_id'),
        ('user_balances', 'user_id'),
        ('api_reloads', 'reload_id'),
    ]
    
    for table, id_column in tables_with_text_ids:
        try:
            # Generate UUIDs for rows missing them
            cursor.execute(f"""
                UPDATE {table}
                SET {id_column} = gen_random_uuid()
                WHERE {id_column} IS NULL 
                OR {id_column} !~ '^[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}$'
            """)
            
            if cursor.rowcount > 0:
                results[table] = f"Generated UUIDs for {cursor.rowcount} rows"
                
        except Exception as e:
            results[table] = f"Error: {e}"
    
    conn.commit()
    conn.close()
    
    return results


def create_indexes(db_url: str) -> List[str]:
    """
    Create indexes on commonly queried columns
    """
    indexes = []
    
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # Index definitions
    index_defs = [
        ("idx_users_email", "users", "email"),
        ("idx_conversations_user_id", "conversations", "user_id"),
        ("idx_messages_conversation_id", "messages", "conversation_id"),
        ("idx_agents_user_id", "agents", "user_id"),
        ("idx_api_usage_user_id", "api_usage", "user_id"),
        ("idx_api_usage_created_at", "api_usage", "created_at"),
        ("idx_audit_log_user_id", "audit_log", "user_id"),
        ("idx_audit_log_created_at", "audit_log", "created_at"),
        ("idx_kernel_events_agent_id", "kernel_events", "agent_id"),
        ("idx_kernel_events_created_at", "kernel_events", "created_at"),
    ]
    
    for index_name, table, column in index_defs:
        try:
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS {index_name}
                ON {table} ({column})
            """)
            indexes.append(f"Created index {index_name}")
        except Exception as e:
            indexes.append(f"Error on {index_name}: {e}")
    
    conn.commit()
    conn.close()
    
    return indexes


def run_migration(db_url: str) -> Dict:
    """
    Run complete UUID migration
    """
    results = {
        "uuid_columns": create_uuid_columns(db_url),
        "backfill": backfill_uuid_ids(db_url),
        "indexes": create_indexes(db_url)
    }
    
    return results
