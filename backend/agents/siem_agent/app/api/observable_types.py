"""Observable types endpoint for compatibility with SOAR Agent."""

from fastapi import APIRouter

router = APIRouter(prefix="/siem", tags=["observables"])


@router.get("/observables/types")
def get_observable_types():
    """
    Get available observable data types.
    
    This endpoint provides compatibility with SOAR Agent's observable extraction.
    """
    return {
        "types": [
            {"id": "ip", "label": "IP Address"},
            {"id": "domain", "label": "Domain"},
            {"id": "url", "label": "URL"},
            {"id": "hash_md5", "label": "Hash (MD5)"},
            {"id": "hash_sha1", "label": "Hash (SHA1)"},
            {"id": "hash_sha256", "label": "Hash (SHA256)"},
            {"id": "email", "label": "Email Address"},
            {"id": "filename", "label": "Filename"},
            {"id": "filepath", "label": "File Path"},
            {"id": "registry", "label": "Registry Key"},
            {"id": "user-agent", "label": "User Agent"},
            {"id": "autonomous-system", "label": "Autonomous System"},
        ]
    }

