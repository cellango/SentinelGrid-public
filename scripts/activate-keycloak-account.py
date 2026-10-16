#!/usr/bin/env python3
"""
Script to activate a Keycloak user account.

Tries API-based activation first, falls back to UI-based activation if needed.
"""

import sys
import os
import argparse
import logging

# Add backend/tests to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'tests'))

try:
    from helpers.keycloak_account_setup import setup_test_user
except ImportError:
    setup_test_user = None

try:
    from helpers.keycloak_kcadm_setup import activate_account_via_kcadm
except ImportError:
    activate_account_via_kcadm = None

try:
    from helpers.keycloak_activate_api import activate_account_via_api
except ImportError:
    activate_account_via_api = None

try:
    from selenium_test_account_activation import KeycloakUIActivation
except ImportError:
    KeycloakUIActivation = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Activate a Keycloak user account')
    parser.add_argument('--keycloak-url', default='http://localhost:8081',
                       help='Keycloak base URL')
    parser.add_argument('--realm', default='agribotsai',
                       help='Realm name')
    parser.add_argument('--username', required=True,
                       help='Username to activate')
    parser.add_argument('--password', required=True,
                       help='Password to set')
    parser.add_argument('--admin-username', default='admin',
                       help='Admin username')
    parser.add_argument('--admin-password', default='admin',
                       help='Admin password')
    parser.add_argument('--use-ui', action='store_true',
                       help='Use UI-based activation (Selenium)')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run browser in headless mode (for UI activation)')
    
    args = parser.parse_args()
    
    logger.info(f"Activating account for {args.username} in realm {args.realm}...")
    
    # Try API-based activation first (unless --use-ui is specified)
    if not args.use_ui:
        # Try complete API activation first (most comprehensive)
        if activate_account_via_api:
            logger.info("Attempting complete API-based activation (recreate user + disable required actions)...")
            try:
                success = activate_account_via_api(
                    args.realm,
                    args.username,
                    args.username,  # Use username as email
                    args.password,
                    args.keycloak_url,
                    verify=True
                )
                if success:
                    logger.info("✅✅✅ Account activated via complete API method! Token generation confirmed!")
                    return 0
                else:
                    logger.warning("Complete API activation did not succeed, trying other methods...")
            except Exception as e:
                logger.warning(f"Complete API activation failed: {e}")
        
        # Try kcadm.sh-based activation (fallback)
        if activate_account_via_kcadm:
            logger.info("Attempting kcadm.sh-based activation (via Docker)...")
            try:
                import time
                success = activate_account_via_kcadm(
                    args.realm,
                    args.username,
                    args.password,
                    admin_user=args.admin_username,
                    admin_password=args.admin_password
                )
                if success:
                    time.sleep(2)  # Give Keycloak a moment to process
                    
                    # Test if token can be obtained
                    import httpx
                    token_url = f"{args.keycloak_url}/realms/{args.realm}/protocol/openid-connect/token"
                    data = {
                        "client_id": "agribotsai-web",
                        "username": args.username,
                        "password": args.password,
                        "grant_type": "password",
                        "scope": "openid",
                    }
                    response = httpx.post(token_url, data=data, timeout=10.0)
                    if response.status_code == 200:
                        logger.info("✅✅✅ Account activated via kcadm.sh! Token generation confirmed!")
                        return 0
                    else:
                        logger.warning(f"⚠️  kcadm activation succeeded but token generation failed: {response.text[:200]}")
            except Exception as e:
                logger.warning(f"kcadm.sh-based activation failed: {e}")
        
        # Fallback to Admin REST API
        if setup_test_user:
            logger.info("Attempting Admin REST API-based activation...")
            try:
                success = setup_test_user(
                    args.keycloak_url,
                    args.realm,
                    args.username,
                    args.password,
                    args.admin_username,
                    args.admin_password
                )
                if success:
                    logger.info("✅ Account activated via Admin REST API!")
                    
                    # Test if token can be obtained
                    import httpx
                    import time
                    time.sleep(2)
                    token_url = f"{args.keycloak_url}/realms/{args.realm}/protocol/openid-connect/token"
                    data = {
                        "client_id": "agribotsai-web",
                        "username": args.username,
                        "password": args.password,
                        "grant_type": "password",
                        "scope": "openid",
                    }
                    response = httpx.post(token_url, data=data, timeout=10.0)
                    if response.status_code == 200:
                        logger.info("✅ Token generation confirmed - account is fully activated!")
                        return 0
                    else:
                        logger.warning(f"⚠️  API activation reported success but token generation failed: {response.text[:200]}")
                        logger.info("Trying UI-based activation as fallback...")
            except Exception as e:
                logger.warning(f"Admin REST API-based activation failed: {e}")
                logger.info("Trying UI-based activation as fallback...")
    
    # UI-based activation (final fallback)
    if KeycloakUIActivation:
        headless_mode = args.headless if args.use_ui else False  # Default to visible if explicitly using UI
        logger.info(f"Attempting UI-based activation (Selenium, headless={headless_mode})...")
        try:
            browser = KeycloakUIActivation(headless=headless_mode)
            try:
                success = browser.activate_account_via_ui(
                    args.keycloak_url,
                    args.realm,
                    args.username,
                    args.password,  # Current password
                    args.password,  # New password
                    "agribotsai-web",
                    "http://localhost:3000"
                )
                if success:
                    logger.info("✅ Account activated via UI!")
                    return 0
                else:
                    logger.error("❌ UI-based activation failed")
                    return 1
            finally:
                browser.close()
        except Exception as e:
            logger.error(f"UI-based activation failed: {e}", exc_info=True)
            if "selenium" in str(e).lower() or "webdriver" in str(e).lower():
                logger.error("Selenium is not properly installed. Install with: pip install selenium webdriver-manager")
            return 1
    else:
        logger.error("❌ No activation methods available. Install Selenium for UI-based activation.")
        return 1


if __name__ == '__main__':
    sys.exit(main())

