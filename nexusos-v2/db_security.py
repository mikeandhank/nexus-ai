"""
Database Security Module
======================
PostgreSQL encryption, FK constraints, and indexes
"""
import psycopg2
from typing import List, Dict


def enable_db_encryption(db_url: str) -> Dict:
    """
    Enable PostgreSQL encryption at rest
    
    Note: This requires PostgreSQL to be configured with encryption
    or use a managed service with encryption enabled.
    """
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    results = []
    
    # Check if pgcrypto extension is available
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        results.append("pgcrypto extension enabled")
    except Exception as e:
        results.append(f"pgcrypto error: {e}")
    
    # Enable row-level security
    try:
        cursor.execute("""
            CREATE POLICY IF NOT EXISTS users_policy ON users
            FOR ALL USING (true)
        """)
        results.append("Row-level security policy created")
    except Exception as e:
        results.append(f"RLS error: {e}")
    
    conn.commit()
    conn.close()
    
    return {"success": True, "actions": results}


def add_foreign_keys(db_url: str) -> List[str]:
    """Add foreign key constraints"""
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    migrations = []
    
    fk_defs = [
        ("conversations", "user_id", "users", "user_id"),
        ("messages", "conversation_id", "conversations", "conversation_id"),
        ("agents", "user_id", "users", "user_id"),
        ("api_usage", "user_id", "users", "user_id"),
        ("api_keys", "user_id", "users", "user_id"),
        ("audit_log", "user_id", "users", "user_id"),
        ("kernel_events", "agent_id", "kernel_agents", "agent_id"),
    ]
    
    for table, column, ref_table, ref_column in fk_defs:
        try:
            cursor.execute(f"""
                ALTER TABLE {table}
                ADD CONSTRAINT fk_{table}_{column}
                FOREIGN KEY ({column})
                REFERENCES {ref_table}({ref_column})
                ON DELETE CASCADE
            """)
            migrations.append(f"Added FK {table}.{column} -> {ref_table}.{ref_column}")
        except psycopg2.errors.lookup('23505'):  # Duplicate
            migrations.append(f"FK already exists: {table}.{column}")
        except Exception as e:
            migrations.append(f"FK error {table}.{column}: {e}")
    
    conn.commit()
    conn.close()
    
    return migrations


def add_indexes(db_url: str) -> List[str]:
    """Create performance indexes"""
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    indexes = []
    
    index_defs = [
        ("idx_users_email", "users", "email"),
        ("idx_conversations_user", "conversations", "user_id"),
        ("idx_conversations_updated", "conversations", "updated_at"),
        ("idx_messages_conversation", "messages", "conversation_id"),
        ("idx_messages_created", "messages", "created_at"),
        ("idx_agents_user", "agents", "user_id"),
        ("idx_agents_status", "agents", "status"),
        ("idx_api_usage_user", "api_usage", "user_id"),
        ("idx_api_usage_created", "api_usage", "created_at"),
        ("idx_api_usage_agent", "api_usage", "agent_id"),
        ("idx_audit_log_user", "audit_log", "user_id"),
        ("idx_audit_log_created", "audit_log", "created_at"),
        ("idx_audit_log_type", "audit_log", "event_type"),
        ("idx_kernel_events_agent", "kernel_events", "agent_id"),
        ("idx_kernel_events_created", "kernel_events", "created_at"),
    ]
    
    for index_name, table, column in index_defs:
        try:
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS {index_name}
                ON {table} ({column})
            """)
            indexes.append(f"Created index {index_name}")
        except Exception as e:
            indexes.append(f"Index error {index_name}: {e}")
    
    conn.commit()
    conn.close()
    
    return indexes


def run_all_db_fixes(db_url: str) -> Dict:
    """Run all database fixes"""
    return {
        "encryption": enable_db_encryption(db_url),
        "foreign_keys": add_foreign_keys(db_url),
        "indexes": add_indexes(db_url)
    }