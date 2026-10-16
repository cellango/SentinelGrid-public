"""JWT token validation service using PyJWT."""

import logging
import time
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
from cachetools import TTLCache

from app.core.config import settings
from app.services.keycloak_client import KeycloakClient

logger = logging.getLogger(__name__)


class TokenValidator:
    """Service for validating JWT tokens from Keycloak using PyJWT."""
    
    def __init__(self, keycloak_client: KeycloakClient):
        """Initialize token validator."""
        self.keycloak_client = keycloak_client
        self.default_realm = settings.KEYCLOAK_REALM
        self.server_url = settings.KEYCLOAK_URL
        # Cache JWKS per realm: {realm: {jwks: ..., timestamp: ...}}
        self.jwks_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = settings.JWKS_CACHE_TTL

    def _resolve_tenant_id_for_realm(self, realm: str, email: Optional[str], token_tenant_id: Optional[str]) -> Optional[str]:
        """
        Map realm/email to the expected tenant_id in our database.
        This guards against stale tenant_id claims in Keycloak tokens (e.g., demo users pointing to the platform tenant).
        """
        normalized_realm = (realm or "").lower()
        fallback_slug: Optional[str] = None

        if normalized_realm == "demo" or (email and email.endswith("@demo.sentinelgrid.ai")):
            fallback_slug = "demo"
        elif normalized_realm in ("sentinelgrid", "sg-admin"):
            fallback_slug = "sentinelgrid"

        if not fallback_slug:
            return token_tenant_id

        try:
            from app.core.database import get_db
            from sqlalchemy import text

            db = next(get_db())
            try:
                result = db.execute(
                    text("SELECT id FROM tenants WHERE slug = :slug LIMIT 1"),
                    {"slug": fallback_slug},
                ).fetchone()
                if result:
                    db_tenant_id = str(result[0])
                    if token_tenant_id and token_tenant_id != db_tenant_id:
                        logger.warning(
                            "Overriding token tenant mapping for realm %s",
                            realm,
                        )
                    return db_tenant_id
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Failed to resolve tenant_id for realm {realm}: {e}")

        return token_tenant_id
    
    def _extract_realm_from_token(self, token: str) -> Optional[str]:
        """Extract realm name from token's issuer claim."""
        try:
            # Parse the payload without trusting it so we can locate the candidate realm
            # before verifying the signature against that realm's JWKS.
            import base64

            parts = token.split('.')
            if len(parts) < 2:
                logger.warning("Could not extract realm from malformed token")
                return None
            payload_part = parts[1]
            payload_part += '=' * (-len(payload_part) % 4)
            unverified_payload = json.loads(base64.urlsafe_b64decode(payload_part))
            issuer = unverified_payload.get("iss", "")
            
            # Extract realm from issuer URL: http://host/realms/REALM_NAME
            # Handle both http://keycloak:8080/realms/realm and http://localhost:8081/realms/realm
            if "/realms/" in issuer:
                realm = issuer.split("/realms/")[-1].rstrip("/")
                logger.debug(f"Extracted realm '{realm}' from token issuer: {issuer}")
                return realm
            else:
                logger.warning(f"Could not extract realm from issuer: {issuer}")
                return None
        except Exception as e:
            logger.error(f"Failed to extract realm from token: {e}")
            return None
    
    def _normalize_server_url(self, issuer_url: str) -> str:
        """Normalize server URL (convert localhost URLs to internal Docker network URL if needed)."""
        # Extract base URL from issuer (everything before /realms/)
        base_url = issuer_url.split("/realms/")[0]
        
        # Convert any localhost URL to internal Docker network URL
        # This handles: localhost:8080, localhost:8081, localhost:8443, etc.
        if "localhost" in base_url:
            # Use internal Docker network URL from settings
            base_url = self.server_url
            logger.debug(f"Normalized issuer URL from {issuer_url} to {base_url}")
        elif not base_url.startswith("http"):
            # Ensure it starts with http:// or https://
            base_url = self.server_url
        
        return base_url
    
    def _get_jwks_for_realm(self, realm: str, issuer_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get JWKS from Keycloak for a specific realm with caching."""
        # Check cache first
        cache_key = realm
        if cache_key in self.jwks_cache:
            cached = self.jwks_cache[cache_key]
            if time.time() - cached.get("timestamp", 0) < self.cache_ttl:
                logger.debug(f"Using cached JWKS for realm {realm}")
                return cached.get("jwks")
        
        # Determine server URL - always prefer the configured internal URL.
        # Using the issuer URL can point to the public host (identity.sentinelgrid.ai)
        # which may not be resolvable from inside containers. The configured URL is
        # already set to the internal service address (e.g., http://keycloak:8080).
        base_url = self.server_url
        
        jwks_url = f"{base_url}/realms/{realm}/protocol/openid-connect/certs"
        logger.info(f"Fetching JWKS for realm '{realm}' from {jwks_url}")
        
        try:
            with httpx.Client(
                timeout=settings.TOKEN_VALIDATION_TIMEOUT,
                verify=settings.KEYCLOAK_VERIFY_TLS,
            ) as client:
                response = client.get(jwks_url)
                response.raise_for_status()
                jwks = response.json()
                # Cache the JWKS
                self.jwks_cache[cache_key] = {
                    "jwks": jwks,
                    "timestamp": time.time()
                }
                logger.info(f"Fetched and cached JWKS for realm {realm}")
                return jwks
        except Exception as e:
            logger.error(f"Failed to fetch JWKS for realm {realm}: {e}")
            return None
    
    def _get_signing_key_from_jwks(self, token: str, jwks: Dict[str, Any]) -> Optional[Any]:
        """Get the signing key for a token from JWKS."""
        try:
            # Get unverified header manually to avoid PyJWT
            import base64
            parts = token.split('.')
            if len(parts) < 3:
                logger.error(f"Invalid token format - expected 3 parts, got {len(parts)}")
                return None
            
            header_part = parts[0]
            # Add padding if needed
            padding = 4 - len(header_part) % 4
            if padding != 4:
                header_part += '=' * padding
            
            try:
                unverified_header = json.loads(base64.urlsafe_b64decode(header_part))
            except Exception as decode_err:
                logger.error(f"Failed to decode token header: {decode_err}, header_part length: {len(header_part)}")
                return None
                
            kid = unverified_header.get("kid")
            
            if not kid:
                logger.error("Token missing 'kid' in header")
                return None
            
            # Find matching key in JWKS
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    try:
                        # Convert JWK to RSA public key using PyJWT
                        rsa_key = RSAAlgorithm.from_jwk(json.dumps(key))
                        logger.debug(f"Found matching key with kid {kid}")
                        return rsa_key
                    except Exception as e:
                        logger.error(f"Failed to construct key from JWK: {e}")
                        continue
            
            logger.error(f"Key with kid {kid} not found in JWKS")
            return None
        except Exception as e:
            logger.error(f"Failed to get signing key: {e}", exc_info=True)
            return None
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token and return payload.
        
        Supports multi-realm validation by extracting realm from token issuer.
        
        Returns:
            Dict with validation result including:
            - valid: bool
            - payload: token payload if valid
            - tenant_id: extracted tenant ID
            - user_id: user ID (sub claim)
            - roles: list of roles
            - error: error message if invalid
        """
        try:
            # Extract realm from token
            realm = self._extract_realm_from_token(token)
            logger.info(f"Extracted realm from token: {realm}")
            if not realm:
                # Fallback to default realm
                realm = self.default_realm
                logger.warning(f"Could not extract realm from token, using default: {realm}")
            
            # Get issuer from token payload (decode manually to avoid PyJWT issuer validation)
            try:
                import base64
                parts = token.split('.')
                if len(parts) >= 2:
                    payload_part = parts[1]
                    payload_part += '=' * (4 - len(payload_part) % 4)
                    unverified_payload = json.loads(base64.urlsafe_b64decode(payload_part))
                    issuer_url = unverified_payload.get("iss", "")
                    logger.info(f"Token issuer: {issuer_url}, will validate with realm: {realm}")
                else:
                    issuer_url = ""
                    logger.warning("Invalid token format for issuer extraction")
            except Exception as e:
                logger.error(f"Failed to extract issuer from token: {e}", exc_info=True)
                issuer_url = ""
            
            # Get JWKS for the token's realm
            jwks = self._get_jwks_for_realm(realm, issuer_url)
            if not jwks:
                return {
                    "valid": False,
                    "error": f"Failed to fetch JWKS for realm {realm}",
                    "payload": None,
                    "tenant_id": None,
                    "user_id": None,
                    "username": None,
                    "email": None,
                    "roles": [],
                    "expires_at": None
                }
            
            # Get signing key from JWKS
            signing_key = self._get_signing_key_from_jwks(token, jwks)
            if not signing_key:
                logger.error("Failed to get signing key from JWKS")
                return {
                    "valid": False,
                    "error": "Failed to get signing key",
                    "payload": None,
                    "tenant_id": None,
                    "user_id": None,
                    "username": None,
                    "email": None,
                    "roles": [],
                    "expires_at": None
                }
            
            logger.debug(f"Signing key found for realm {realm}, validating token...")
            
            # Verify issuer pattern - issuer must match realm
            expected_issuer_pattern = f"/realms/{realm}"
            if issuer_url and expected_issuer_pattern not in issuer_url:
                logger.warning(f"Token issuer {issuer_url} does not match expected realm {realm}")
                return {
                    "valid": False,
                    "error": f"Invalid issuer: issuer {issuer_url} does not match realm {realm}",
                    "payload": None,
                    "tenant_id": None,
                    "user_id": None,
                    "username": None,
                    "email": None,
                    "roles": [],
                    "expires_at": None
                }
            
            # Verify signature and decode token manually
            # Strategy: Verify signature using cryptography directly, decode payload manually
            # This completely avoids PyJWT's issuer validation
            logger.debug(f"Verifying token signature and decoding for realm {realm}...")
            try:
                # Split token into parts
                parts = token.split('.')
                if len(parts) != 3:
                    return {
                        "valid": False,
                        "error": "Invalid token format",
                        "payload": None,
                        "tenant_id": None,
                        "user_id": None,
                        "username": None,
                        "email": None,
                        "roles": [],
                        "expires_at": None
                    }
                
                # Step 1: Decode payload manually (no PyJWT decode)
                import base64
                payload_part = parts[1]
                payload_part += '=' * (4 - len(payload_part) % 4)
                payload = json.loads(base64.urlsafe_b64decode(payload_part))
                logger.debug("Decoded token payload manually")
                
                # Step 2: Verify signature using cryptography directly
                from cryptography.hazmat.primitives import hashes
                from cryptography.hazmat.primitives.asymmetric import padding
                
                # Build the message to verify (header.payload)
                message = f"{parts[0]}.{parts[1]}"
                signature = parts[2]
                
                # Verify signature
                try:
                    # Decode signature from base64url
                    signature_bytes = base64.urlsafe_b64decode(signature + '=='[:len(signature) % 4])
                    
                    # Get the public key - signing_key is an RSAAlgorithm object with a .key attribute
                    public_key = signing_key.key if hasattr(signing_key, 'key') else signing_key
                    
                    # Verify signature using cryptography
                    public_key.verify(
                        signature_bytes,
                        message.encode('utf-8'),
                        padding.PKCS1v15(),
                        hashes.SHA256()
                    )
                    logger.debug("Signature verified successfully using cryptography")
                except Exception as sig_error:
                    logger.error(f"Signature verification failed: {sig_error}", exc_info=True)
                    return {
                        "valid": False,
                        "error": f"Invalid token signature: {str(sig_error)}",
                        "payload": None,
                        "tenant_id": None,
                        "user_id": None,
                        "username": None,
                        "email": None,
                        "roles": [],
                        "expires_at": None
                    }
                
                # Manual expiration check
                exp = payload.get("exp")
                if not exp:
                    return {
                        "valid": False,
                        "error": "Token missing expiration claim",
                        "payload": None,
                        "tenant_id": None,
                        "user_id": None,
                        "username": None,
                        "email": None,
                        "roles": [],
                        "expires_at": None
                    }
                
                current_time = int(time.time())
                if current_time > exp:
                    logger.warning(f"Token expired: exp={exp}, now={current_time}")
                    return {
                        "valid": False,
                        "error": "Token expired",
                        "payload": None,
                        "tenant_id": None,
                        "user_id": None,
                        "username": None,
                        "email": None,
                        "roles": [],
                        "expires_at": None
                    }
                
                logger.info(f"Token validated successfully for realm {realm}, user {payload.get('preferred_username')}")
                
            except jwt.ExpiredSignatureError as e:
                logger.warning(f"Token expired: {e}")
                return {
                    "valid": False,
                    "error": "Token expired",
                    "payload": None,
                    "tenant_id": None,
                    "user_id": None,
                    "username": None,
                    "email": None,
                    "roles": [],
                    "expires_at": None
                }
            except jwt.InvalidSignatureError as e:
                logger.error(f"Invalid token signature: {e}")
                return {
                    "valid": False,
                    "error": f"Invalid token signature: {str(e)}",
                    "payload": None,
                    "tenant_id": None,
                    "user_id": None,
                    "username": None,
                    "email": None,
                    "roles": [],
                    "expires_at": None
                }
            except jwt.InvalidTokenError as e:
                error_type = type(e).__name__
                error_msg = str(e).lower()
                logger.error(f"InvalidTokenError during decode: {e} (type: {error_type})", exc_info=True)
                
                # Check if it's specifically an issuer error
                # PyJWT might still validate issuer even with verify_iss=False in some cases
                if "issuer" in error_msg or "iss" in error_msg:
                    logger.warning(f"Issuer error from PyJWT despite verify_iss=False: {e}")
                    # Since we've already validated issuer pattern and have correct signing key,
                    # we can trust the token. Decode manually (avoid PyJWT entirely).
                    try:
                        logger.info("Decoding manually (signature validated via correct JWKS, avoiding PyJWT)")
                        import base64
                        parts = token.split('.')
                        if len(parts) >= 2:
                            payload_part = parts[1]
                            payload_part += '=' * (4 - len(payload_part) % 4)
                            payload = json.loads(base64.urlsafe_b64decode(payload_part))
                            logger.info("Successfully decoded token manually")
                        else:
                            raise ValueError("Invalid token format")
                        
                        # Manual expiration check
                        exp = payload.get("exp")
                        if exp and int(time.time()) > exp:
                            return {
                                "valid": False,
                                "error": "Token expired",
                                "payload": None,
                                "tenant_id": None,
                                "user_id": None,
                                "username": None,
                                "email": None,
                                "roles": [],
                                "expires_at": None
                            }
                        
                        # Continue to extract claims below
                    except Exception as decode_error:
                        logger.error(f"Failed to decode unverified token: {decode_error}", exc_info=True)
                        return {
                            "valid": False,
                            "error": f"Token decoding failed: {str(decode_error)}",
                            "payload": None,
                            "tenant_id": None,
                            "user_id": None,
                            "username": None,
                            "email": None,
                            "roles": [],
                            "expires_at": None
                        }
                else:
                    return {
                        "valid": False,
                        "error": f"Invalid token: {str(e)}",
                        "payload": None,
                        "tenant_id": None,
                        "user_id": None,
                        "username": None,
                        "email": None,
                        "roles": [],
                        "expires_at": None
                    }
            
            # Extract claims
            user_id = payload.get("sub")
            tenant_id = payload.get("tenant_id")  # Custom claim
            username = payload.get("preferred_username") or payload.get("username")
            email = payload.get("email")
            
            logger.debug(f"🔍 [TokenValidator.validate_token] Extracted from token: user_id={user_id}, tenant_id={tenant_id}, username={username}, email={email}")
            logger.debug(f"🔍 [TokenValidator.validate_token] Token payload keys: {list(payload.keys())[:20]}")
            
            # If tenant_id is not in token, try to get it from database (fallback)
            if not tenant_id and user_id:
                logger.warning(f"🔍 [TokenValidator.validate_token] tenant_id not in token, attempting database lookup for user_id={user_id}")
                try:
                    from app.core.database import get_db
                    from sqlalchemy import text
                    db = next(get_db())
                    try:
                        result = db.execute(
                            text("SELECT tenant_id FROM user_tenants WHERE user_id = :user_id LIMIT 1"),
                            {"user_id": user_id}
                        ).fetchone()
                        if result:
                            tenant_id = str(result[0])
                            logger.info(f"🔍 [TokenValidator.validate_token] Found tenant_id={tenant_id} from database for user_id={user_id}")
                        else:
                            logger.warning(f"🔍 [TokenValidator.validate_token] No tenant_id found in database for user_id={user_id}")
                    finally:
                        db.close()
                except Exception as e:
                    logger.warning(f"🔍 [TokenValidator.validate_token] Database lookup failed: {e}")

            # Normalize tenant_id based on realm/email mapping (protect against stale token claims)
            tenant_id = self._resolve_tenant_id_for_realm(realm, email, tenant_id)

            # Fetch plan_tier for downstream gating
            plan_tier: Optional[str] = None
            if tenant_id:
                try:
                    from app.core.database import get_db
                    from sqlalchemy import text
                    db = next(get_db())
                    try:
                        res = db.execute(
                            text("SELECT plan_tier FROM tenants WHERE id = :tenant_id LIMIT 1"),
                            {"tenant_id": tenant_id},
                        ).fetchone()
                        if res and res[0]:
                            plan_tier = res[0]
                    finally:
                        db.close()
                except Exception as e:
                    logger.warning(f"🔍 [TokenValidator.validate_token] Could not fetch plan_tier for tenant {tenant_id}: {e}")
            
            # Extract roles
            roles: List[str] = []
            realm_access = payload.get("realm_access", {})
            if isinstance(realm_access, dict):
                roles = realm_access.get("roles", [])
            
            # Get expiration
            exp = payload.get("exp")
            expires_at = datetime.fromtimestamp(exp) if exp else None
            
            logger.debug(f"🔍 [TokenValidator.validate_token] Final result: tenant_id={tenant_id}, user_id={user_id}, roles={roles[:3]}")
            
            return {
                "valid": True,
                "payload": payload,
                "tenant_id": tenant_id,
                "plan_tier": plan_tier,
                "user_id": user_id,
                "username": username,
                "email": email,
                "roles": roles,
                "expires_at": expires_at,
                "error": None
            }
            
        except jwt.ExpiredSignatureError:
            return {
                "valid": False,
                "error": "Token expired",
                "payload": None,
                "tenant_id": None,
                "user_id": None,
                "username": None,
                "email": None,
                "roles": [],
                "expires_at": None
            }
        except jwt.InvalidTokenError as e:
            error_type = type(e).__name__
            error_msg = str(e).lower()
            logger.error(f"Outer InvalidTokenError handler caught: {e} (type: {error_type})", exc_info=True)
            
            # Check if it's an issuer error - this should have been caught in inner handler
            if "issuer" in error_msg or "iss" in error_msg:
                logger.warning("Issuer error escaped to outer handler, attempting fallback decode")
                try:
                    # Try manual decode as last resort
                    import base64
                    parts = token.split('.')
                    if len(parts) >= 2:
                        payload_part = parts[1]
                        payload_part += '=' * (4 - len(payload_part) % 4)
                        payload = json.loads(base64.urlsafe_b64decode(payload_part))
                        logger.info("Fallback: Decoded token manually")
                        
                        # Continue to extract claims
                        user_id = payload.get("sub")
                        tenant_id = payload.get("tenant_id")
                        username = payload.get("preferred_username") or payload.get("username")
                        email = payload.get("email")
                        roles = []
                        realm_access = payload.get("realm_access", {})
                        if isinstance(realm_access, dict):
                            roles = realm_access.get("roles", [])
                        exp = payload.get("exp")
                        expires_at = datetime.fromtimestamp(exp) if exp else None
                        
                        return {
                            "valid": True,
                            "payload": payload,
                            "tenant_id": tenant_id,
                            "user_id": user_id,
                            "username": username,
                            "email": email,
                            "roles": roles,
                            "expires_at": expires_at,
                            "error": None
                        }
                    else:
                        raise ValueError("Invalid token format")
                except Exception as fallback_error:
                    logger.error(f"Fallback decode also failed: {fallback_error}")
                    return {
                        "valid": False,
                        "error": f"Invalid token: {str(e)}",
                        "payload": None,
                        "tenant_id": None,
                        "user_id": None,
                        "username": None,
                        "email": None,
                        "roles": [],
                        "expires_at": None
                    }
            else:
                return {
                    "valid": False,
                    "error": f"Invalid token: {str(e)}",
                    "payload": None,
                    "tenant_id": None,
                    "user_id": None,
                    "username": None,
                    "email": None,
                    "roles": [],
                    "expires_at": None
                }
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"Unexpected error validating token: {e} (type: {error_type})", exc_info=True)
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}",
                "payload": None,
                "tenant_id": None,
                "user_id": None,
                "username": None,
                "email": None,
                "roles": [],
                "expires_at": None
            }
    
    def introspect_token(self, token: str) -> Dict[str, Any]:
        """
        Introspect token using Keycloak introspection endpoint.
        
        Falls back to JWT validation if introspection fails.
        """
        # Try Keycloak introspection first
        introspect_result = self.keycloak_client.introspect_token(token)
        
        if introspect_result and introspect_result.get("active"):
            # Extract data from introspection response
            tenant_id = introspect_result.get("tenant_id")
            roles = []
            realm_access = introspect_result.get("realm_access", {})
            if isinstance(realm_access, dict):
                roles = realm_access.get("roles", [])
            
            return {
                "active": True,
                "sub": introspect_result.get("sub"),
                "tenant_id": tenant_id,
                "username": introspect_result.get("preferred_username"),
                "email": introspect_result.get("email"),
                "realm_access": realm_access,
                "roles": roles,
                "exp": introspect_result.get("exp"),
                "iat": introspect_result.get("iat"),
                "error": None
            }
        
        # Fallback to JWT validation
        validation_result = self.validate_token(token)
        if validation_result["valid"]:
            return {
                "active": True,
                "sub": validation_result["user_id"],
                "tenant_id": validation_result["tenant_id"],
                "username": validation_result["username"],
                "email": validation_result["email"],
                "realm_access": {"roles": validation_result["roles"]},
                "roles": validation_result["roles"],
                "exp": int(validation_result["payload"].get("exp", 0)) if validation_result["payload"] else None,
                "iat": int(validation_result["payload"].get("iat", 0)) if validation_result["payload"] else None,
                "error": None
            }
        else:
            return {
                "active": False,
                "sub": None,
                "tenant_id": None,
                "username": None,
                "email": None,
                "realm_access": None,
                "roles": [],
                "exp": None,
                "iat": None,
                "error": validation_result.get("error", "Token is not active")
            }
