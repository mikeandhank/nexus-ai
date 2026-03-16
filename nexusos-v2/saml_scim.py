"""
SAML/SCIM Integration - Enterprise Identity
========================================
Supports SAML 2.0 for SSO and SCIM for user provisioning.
"""

import os
import json
import uuid
import logging
from typing import Dict, List, Optional
from datetime import datetime
import hashlib
import base64
import xml.etree.ElementTree as ET

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SAMLIdP:
    """
    SAML 2.0 Identity Provider
    
    Supports:
    - Okta
    - Azure AD
    - OneLogin
    - Generic SAML IdP
    """
    
    def __init__(self):
        self.providers: Dict[str, Dict] = {}
    
    def create_sp_metadata(self, entity_id: str, acs_url: str) -> str:
        """Generate Service Provider metadata XML"""
        
        metadata = f'''<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
                     entityID="{entity_id}">
    <md:SPSSODescriptor AuthnRequestsSigned="false" 
                       WantAssertionsSigned="true"
                       protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>
        <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                              Location="{acs_url}"
                              index="0"/>
    </md:SPSSODescriptor>
</md:EntityDescriptor>'''
        return metadata
    
    def parse_saml_response(self, saml_response: str) -> Dict:
        """Parse SAML response and extract user info"""
        
        try:
            # Decode base64
            decoded = base64.b64decode(saml_response)
            
            # Parse XML
            root = ET.fromstring(decoded)
            
            # Extract namespace
            ns = {'saml': 'urn:oasis:names:tc:SAML:2.0:assertion'}
            
            # Get attributes
            attributes = {}
            for attr in root.findall('.//saml:Attribute', ns):
                name = attr.get('Name')
                values = [v.text for v in attr.findall('saml:AttributeValue', ns)]
                if values:
                    attributes[name] = values[0] if len(values) == 1 else values
            
            # Get name ID
            name_id = root.find('.//saml:NameID', ns)
            user_id = name_id.text if name_id is not None else attributes.get('email')
            
            return {
                "success": True,
                "user_id": user_id,
                "email": attributes.get('email', attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress')),
                "name": attributes.get('name', attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name')),
                "first_name": attributes.get('firstName', attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname')),
                "last_name": attributes.get('lastName', attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname')),
                "groups": attributes.get('groups', []),
                "raw_attributes": attributes
            }
            
        except Exception as e:
            logger.error(f"SAML parse error: {e}")
            return {"success": False, "error": str(e)}
    
    def generate_saml_request(self, entity_id: str, acs_url: str, 
                           provider_id: str) -> str:
        """Generate SAML authentication request"""
        
        request_id = f"_{uuid.uuid4().hex}"
        issue_instant = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        
        saml_request = f'''<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                   ID="{request_id}"
                   Version="2.0"
                   IssueInstant="{issue_instant}"
                   AssertionConsumerServiceURL="{acs_url}"
                   ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">{entity_id}</saml:Issuer>
    <samlp:NameIDPolicy Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
                      AllowCreate="true"/>
</samlp:AuthnRequest>'''
        
        # Base64 encode
        encoded = base64.b64encode(saml_request.encode()).decode()
        
        return encoded


class SCIMClient:
    """
    SCIM 2.0 Client for User Provisioning
    
    Supports:
    - User provisioning/deprovisioning
    - Group management
    - Attribute mapping
    """
    
    def __init__(self, base_url: str = None, bearer_token: str = None):
        self.base_url = base_url
        self.bearer_token = bearer_token
    
    def set_credentials(self, base_url: str, bearer_token: str):
        """Set SCIM credentials"""
        self.base_url = base_url
        self.bearer_token = bearer_token
    
    def create_user(self, user_data: Dict) -> Dict:
        """Create a user via SCIM"""
        import requests
        
        user_schema = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": user_data.get("email"),
            "name": {
                "givenName": user_data.get("first_name", ""),
                "familyName": user_data.get("last_name", "")
            },
            "emails": [{
                "value": user_data.get("email"),
                "primary": True
            }],
            "active": user_data.get("active", True)
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/Users",
                json=user_schema,
                headers={
                    "Authorization": f"Bearer {self.bearer_token}",
                    "Content-Type": "application/scim+json"
                },
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                return {"success": True, "user": response.json()}
            else:
                return {"success": False, "error": f"Status {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def update_user(self, user_id: str, user_data: Dict) -> Dict:
        """Update a user via SCIM"""
        import requests
        
        update_schema = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        }
        
        if "first_name" in user_data or "last_name" in user_data:
            update_schema["name"] = {}
            if "first_name" in user_data:
                update_schema["name"]["givenName"] = user_data["first_name"]
            if "last_name" in user_data:
                update_schema["name"]["familyName"] = user_data["last_name"]
        
        if "active" in user_data:
            update_schema["active"] = user_data["active"]
        
        try:
            response = requests.patch(
                f"{self.base_url}/Users/{user_id}",
                json=update_schema,
                headers={
                    "Authorization": f"Bearer {self.bearer_token}",
                    "Content-Type": "application/scim+json"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return {"success": True, "user": response.json()}
            else:
                return {"success": False, "error": f"Status {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete_user(self, user_id: str) -> Dict:
        """Delete (deprovision) a user"""
        import requests
        
        try:
            response = requests.delete(
                f"{self.base_url}/Users/{user_id}",
                headers={"Authorization": f"Bearer {self.bearer_token}"},
                timeout=30
            )
            
            return {"success": response.status_code in [200, 204]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_user(self, user_id: str) -> Dict:
        """Get a user by ID"""
        import requests
        
        try:
            response = requests.get(
                f"{self.base_url}/Users/{user_id}",
                headers={"Authorization": f"Bearer {self.bearer_token}"},
                timeout=30
            )
            
            if response.status_code == 200:
                return {"success": True, "user": response.json()}
            else:
                return {"success": False, "error": f"Status {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_users(self, start_index: int = 1, count: int = 100) -> Dict:
        """List users"""
        import requests
        
        try:
            response = requests.get(
                f"{self.base_url}/Users",
                params={"startIndex": start_index, "count": count},
                headers={"Authorization": f"Bearer {self.bearer_token}"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "users": data.get("Resources", []),
                    "total": data.get("totalResults", 0)
                }
            else:
                return {"success": False, "error": f"Status {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_group(self, group_name: str) -> Dict:
        """Create a group"""
        import requests
        
        group_schema = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
            "displayName": group_name
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/Groups",
                json=group_schema,
                headers={
                    "Authorization": f"Bearer {self.bearer_token}",
                    "Content-Type": "application/scim+json"
                },
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                return {"success": True, "group": response.json()}
            else:
                return {"success": False, "error": f"Status {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def add_user_to_group(self, user_id: str, group_id: str) -> Dict:
        """Add user to group"""
        import requests
        
        # Get current group members
        response = requests.get(
            f"{self.base_url}/Groups/{group_id}",
            headers={"Authorization": f"Bearer {self.bearer_token}"},
            timeout=30
        )
        
        if response.status_code != 200:
            return {"success": False, "error": "Group not found"}
        
        group = response.json()
        members = group.get("members", [])
        
        # Add user
        members.append({"value": user_id, "$ref": f"Users/{user_id}"})
        
        # Update group
        response = requests.patch(
            f"{self.base_url}/Groups/{group_id}",
            json={
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
                "members": members
            },
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/scim+json"
            },
            timeout=30
        )
        
        return {"success": response.status_code == 200}


# Integration with SAML/SCIM
class EnterpriseIdentityManager:
    """
    Manages SAML SSO and SCIM provisioning.
    """
    
    def __init__(self):
        self.saml = SAMLIdP()
        self.scim = SCIMClient()
    
    def configure_saml(self, provider: str, config: Dict) -> Dict:
        """Configure SAML provider"""
        self.saml.providers[provider] = config
        return {"success": True, "provider": provider}
    
    def configure_scim(self, base_url: str, bearer_token: str) -> Dict:
        """Configure SCIM client"""
        self.scim.set_credentials(base_url, bearer_token)
        return {"success": True}
    
    def handle_saml_callback(self, saml_response: str) -> Dict:
        """Handle SAML authentication callback"""
        return self.saml.parse_saml_response(saml_response)
    
    def provision_user(self, user_data: Dict) -> Dict:
        """Provision user via SCIM"""
        return self.scim.create_user(user_data)
    
    def deprovision_user(self, user_id: str) -> Dict:
        """Deprovision user via SCIM"""
        return self.scim.delete_user(user_id)
    
    def sync_users(self) -> Dict:
        """Sync users from SCIM server"""
        return self.scim.list_users()


# Singleton
_identity_manager = None

def get_identity_manager() -> EnterpriseIdentityManager:
    global _identity_manager
    if _identity_manager is None:
        _identity_manager = EnterpriseIdentityManager()
    return _identity_manager
