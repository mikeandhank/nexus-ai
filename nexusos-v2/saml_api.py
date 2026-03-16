"""
NexusOS SAML/SCIM Integration
Enterprise SSO support for Okta, Azure AD, OneLogin, etc.
"""

import os
import json
from flask import Flask, request, jsonify, redirect

# SAML Auth enabled via python3-saml
# Configuration is loaded from environment variables

def setup_saml_routes(app):
    """Set up SAML authentication routes"""
    
    # Lazy import to avoid errors if python3-saml not installed
    try:
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
        from onelogin.saml2.settings import OneLogin_Saml2_Settings
        SAML_AVAILABLE = True
    except ImportError:
        SAML_AVAILABLE = False
    
    def get_saml_config():
        """Get SAML configuration from environment"""
        return {
            'strict': True,
            'debug': False,
            'sp': {
                'entityId': os.environ.get('SAML_SP_ENTITY_ID', 'nexusos'),
                'assertionConsumerService': {
                    'url': os.environ.get('SAML_ACS_URL', 'http://localhost:8080/api/auth/saml/callback'),
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST'
                },
                'singleLogoutService': {
                    'url': os.environ.get('SAML_SLO_URL', 'http://localhost:8080/api/auth/saml/logout'),
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                },
                'NameIDFormat': 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress'
            },
            'idp': {
                'entityId': os.environ.get('SAML_IDP_ENTITY_ID', ''),
                'singleSignOnService': {
                    'url': os.environ.get('SAML_IDP_SSO_URL', ''),
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                },
                'singleLogoutService': {
                    'url': os.environ.get('SAML_IDP_SLO_URL', ''),
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                },
                'x509cert': os.environ.get('SAML_IDP_CERT', '')
            }
        }
    
    @app.route('/api/auth/saml/login')
    def saml_login():
        """Initiate SAML login"""
        if not SAML_AVAILABLE:
            return jsonify({'status': 'error', 'message': 'SAML not configured'}), 501
        
        try:
            req = {
                'https': 'on' if request.is_secure else 'off',
                'http_host': request.host,
                'script_name': request.path,
                'get_data': request.args.copy(),
                'post_data': request.form.copy()
            }
            
            auth = OneLogin_Saml2_Auth(req, get_saml_config())
            return redirect(auth.login())
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'SAML error: {str(e)}'}), 500
    
    @app.route('/api/auth/saml/callback', methods=['POST'])
    def saml_callback():
        """Handle SAML response"""
        if not SAML_AVAILABLE:
            return jsonify({'status': 'error', 'message': 'SAML not configured'}), 501
        
        try:
            req = {
                'https': 'on' if request.is_secure else 'off',
                'http_host': request.host,
                'script_name': request.path,
                'post_data': request.form.copy()
            }
            
            auth = OneLogin_Saml2_Auth(req, get_saml_config())
            auth.process_response()
            
            errors = auth.get_errors()
            if errors:
                return jsonify({'status': 'error', 'message': f'SAML errors: {errors}'}), 400
            
            if not auth.is_authenticated():
                return jsonify({'status': 'error', 'message': 'Authentication failed'}), 401
            
            # Get user attributes
            attrs = auth.get_attributes()
            email = auth.get_nameid()
            
            # TODO: Create or update user in database
            # For now, return the SAML data
            return jsonify({
                'status': 'success',
                'email': email,
                'attributes': attrs,
                'message': 'SAML authentication successful - link to user account in admin'
            })
            
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'SAML error: {str(e)}'}), 500
    
    @app.route('/api/auth/saml/metadata')
    def saml_metadata():
        """Return SAML SP metadata"""
        if not SAML_AVAILABLE:
            return jsonify({'status': 'error', 'message': 'SAML not configured'}), 501
        
        try:
            settings = OneLogin_Saml2_Settings(get_saml_config(), sp_validation=True)
            metadata = settings.get_sp_metadata()
            errors = settings.validate_metadata(metadata)
            
            if errors:
                return jsonify({'status': 'error', 'message': f'Metadata errors: {errors}'}), 500
            
            return metadata, 200, {'Content-Type': 'application/xml'}
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'Error: {str(e)}'}), 500
    
    @app.route('/api/auth/sso-status')
    def sso_status():
        """Check SSO configuration status"""
        return jsonify({
            'saml_configured': SAML_AVAILABLE,
            'saml_enabled': os.environ.get('SAML_IDP_SSO_URL', '') != '',
            'providers': ['SAML 2.0', 'OAuth2/OIDC'] if SAML_AVAILABLE else ['OAuth2/OIDC']
        })
    
    return app
