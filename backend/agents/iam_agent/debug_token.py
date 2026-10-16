#!/usr/bin/env python3
"""
Direct debugging script for token validation.
Run this in the container: docker-compose exec iam_agent python3 /app/debug_token.py
"""

import sys
import os
import json
import logging
import traceback
from pathlib import Path
import httpx

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.services.keycloak_client import KeycloakClient
from app.services.token_validator import TokenValidator

def get_test_token():
    """Get a test token from Keycloak."""
    import httpx
    
    # Use internal Docker network URL when running in container
    keycloak_url = os.getenv('KEYCLOAK_URL', 'http://keycloak:8080')
    realm = os.environ["KEYCLOAK_REALM"]
    token_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token"
    
    try:
        response = httpx.post(
            token_url,
            data={
                'client_id': os.environ['KEYCLOAK_CLIENT_ID'],
                'username': os.environ['KEYCLOAK_TEST_USERNAME'],
                'password': os.environ['KEYCLOAK_TEST_PASSWORD'],
                'grant_type': 'password'
            },
            timeout=10.0
        )
        response.raise_for_status()
        token_data = response.json()
        return token_data.get('access_token')
    except Exception as e:
        print(f"Error getting token: {e}")
        return None


def main():
    print("="*80)
    print("🔍 Token Validation Debug Script")
    print("="*80)
    
    # Get token
    print("\n1️⃣  Getting test token from Keycloak...")
    token = get_test_token()
    if not token:
        sys.exit(1)
    print("✅ Obtained token (value withheld)")
    
    # Initialize validator
    print("\n2️⃣  Initializing TokenValidator...")
    try:
        client = KeycloakClient()
        validator = TokenValidator(client)
        print("✅ TokenValidator initialized")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        traceback.print_exc()
        sys.exit(1)
    
    # Test validation
    print("\n3️⃣  Testing token validation...")
    print("-" * 80)
    try:
        result = validator.validate_token(token)
        print("\n✅ Validation complete!")
        print(f"\nResult:")
        print(json.dumps({
            'valid': result.get('valid'),
            'tenant_id': result.get('tenant_id'),
            'username': result.get('username'),
            'email': result.get('email'),
            'roles': result.get('roles', [])[:5],
            'error': result.get('error')
        }, indent=2))
        
        if not result.get('valid'):
            print(f"\n❌ Validation failed: {result.get('error')}")
            
    except Exception as e:
        print(f"\n❌ Exception during validation: {type(e).__name__}: {e}")
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "="*80)

if __name__ == '__main__':
    main()

