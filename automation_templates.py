"""
Automation Templates Library - Pre-built Workflows
"""

import uuid
from datetime import datetime
from flask import jsonify, request

# Template registry
AUTOMATION_TEMPLATES = {
    'crm_sync': {
        'id': 'crm_sync',
        'name': 'CRM Data Sync',
        'description': 'Automatically sync contacts and deals between systems',
        'triggers': ['new_lead', 'deal_updated', 'contact_created'],
        'actions': ['create_contact', 'update_deal', 'send_notification'],
        'category': 'sales',
        'config_schema': {
            'source_crm': {'type': 'string', 'enum': ['hubspot', 'salesforce', 'pipedrive']},
            'target_system': {'type': 'string'},
            'sync_interval': {'type': 'integer', 'default': 15}
        }
    },
    'email_parser': {
        'id': 'email_parser',
        'name': 'Email Intake Parser',
        'description': 'Parse incoming emails, extract info, route to appropriate handler',
        'triggers': ['email_received'],
        'actions': ['extract_data', 'create_task', 'auto_reply'],
        'category': 'operations',
        'config_schema': {
            'email_folder': {'type': 'string', 'default': 'inbox'},
            'extract_fields': {'type': 'array', 'items': ['name', 'email', 'phone', 'company']},
            'auto_reply_template': {'type': 'string'}
        }
    },
    'support_triage': {
        'id': 'support_triage',
        'name': 'Support Ticket Triage',
        'description': 'AI-powered ticket classification and routing',
        'triggers': ['new_ticket'],
        'actions': ['classify', 'prioritize', 'route_to_queue', 'auto_respond'],
        'category': 'support',
        'config_schema': {
            'priority_keywords': {'type': 'object'},
            'routing_rules': {'type': 'array'},
            'sla_respond_minutes': {'type': 'integer', 'default': 60}
        }
    },
    'invoice_processor': {
        'id': 'invoice_processor',
        'name': 'Invoice Processing',
        'description': 'Extract data from invoices, validate, process payments',
        'triggers': ['invoice_received'],
        'actions': ['extract_data', 'validate', 'approve', 'schedule_payment'],
        'category': 'finance',
        'config_schema': {
            'approval_threshold': {'type': 'number', 'default': 1000},
            'auto_approve_under': {'type': 'number', 'default': 100}
        }
    },
    'content_publisher': {
        'id': 'content_publish',
        'name': 'Content Publishing Workflow',
        'description': 'Draft → Review → Schedule → Publish across platforms',
        'triggers': ['content_approved', 'schedule_time'],
        'actions': ['format_for_platform', 'upload_media', 'publish', 'notify'],
        'category': 'marketing',
        'config_schema': {
            'platforms': {'type': 'array', 'items': ['twitter', 'linkedin', 'blog']},
            'approval_required': {'type': 'boolean', 'default': True}
        }
    },
    'onboarding_flow': {
        'id': 'onboarding',
        'name': 'Customer Onboarding',
        'description': 'Automated new customer welcome and setup sequence',
        'triggers': ['customer_created'],
        'actions': ['send_welcome', 'create_accounts', 'setup_profile', 'schedule_checkin'],
        'category': 'sales',
        'config_schema': {
            'welcome_email_template': {'type': 'string'},
            'days_to_checkin': {'type': 'integer', 'default': 7}
        }
    }
}

# Active automations (user-instantiated)
ACTIVE_AUTOMATIONS = {}

def create_automation_routes(app, require_nexus_key):
    """Register automation template routes"""
    
    @app.route('/api/automations/templates', methods=['GET'])
    @require_nexus_key
    def list_templates():
        """List all automation templates"""
        return jsonify({
            'templates': list(AUTOMATION_TEMPLATES.values())
        })
    
    @app.route('/api/automations/templates/<template_id>', methods=['GET'])
    @require_nexus_key
    def get_template(template_id):
        """Get template details"""
        if template_id not in AUTOMATION_TEMPLATES:
            return jsonify({'error': 'Template not found'}), 404
        return jsonify(AUTOMATION_TEMPLATES[template_id])
    
    @app.route('/api/automations', methods=['POST'])
    @require_nexus_key
    def activate_automation():
        """Activate an automation from a template"""
        data = request.get_json()
        template_id = data.get('template_id')
        
        if template_id not in AUTOMATION_TEMPLATES:
            return jsonify({'error': 'Template not found'}), 404
        
        automation_id = str(uuid.uuid4())
        automation = {
            'id': automation_id,
            'template_id': template_id,
            'name': AUTOMATION_TEMPLATES[template_id]['name'],
            'config': data.get('config', {}),
            'status': 'active',
            'trigger_count': 0,
            'last_triggered': None,
            'created_at': datetime.utcnow().isoformat()
        }
        
        ACTIVE_AUTOMATIONS[automation_id] = automation
        
        return jsonify({
            'automation': automation,
            'message': f'Automation "{automation["name"]}" activated'
        })
    
    @app.route('/api/automations', methods=['GET'])
    @require_nexus_key
    def list_automations():
        """List active automations"""
        return jsonify({
            'automations': list(ACTIVE_AUTOMATIONS.values())
        })
    
    @app.route('/api/automations/<automation_id>/trigger', methods=['POST'])
    @require_nexus_key
    def trigger_automation(automation_id):
        """Manually trigger an automation"""
        if automation_id not in ACTIVE_AUTOMATIONS:
            return jsonify({'error': 'Automation not found'}), 404
        
        automation = ACTIVE_AUTOMATIONS[automation_id]
        trigger_data = request.get_json() or {}
        
        # Simulate automation execution
        template = AUTOMATION_TEMPLATES.get(automation['template_id'])
        
        automation['trigger_count'] += 1
        automation['last_triggered'] = datetime.utcnow().isoformat()
        
        return jsonify({
            'status': 'executed',
            'automation_id': automation_id,
            'actions_executed': template['actions'] if template else [],
            'trigger_data': trigger_data,
            'executed_at': automation['last_triggered']
        })
    
    @app.route('/api/automations/<automation_id>', methods=['DELETE'])
    @require_nexus_key
    def deactivate_automation(automation_id):
        """Deactivate an automation"""
        if automation_id not in ACTIVE_AUTOMATIONS:
            return jsonify({'error': 'Automation not found'}), 404
        
        del ACTIVE_AUTOMATIONS[automation_id]
        return jsonify({'message': 'Automation deactivated'})
    
    @app.route('/api/automations/<automation_id>', methods=['PUT'])
    @require_nexus_key
    def update_automation(automation_id):
        """Update automation config"""
        if automation_id not in ACTIVE_AUTOMATIONS:
            return jsonify({'error': 'Automation not found'}), 404
        
        data = request.get_json()
        ACTIVE_AUTOMATIONS[automation_id]['config'].update(data.get('config', {}))
        
        return jsonify({
            'automation': ACTIVE_AUTOMATIONS[automation_id]
        })
    
    return app
