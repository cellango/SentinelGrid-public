#!/usr/bin/env python3
"""
Seed default access profiles for IAM portal.

This script creates default access profiles that can be assigned to users.
Access profiles are bundles of entitlements that define what a user can access.
"""

import os
import sys
import uuid
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Database URL
DB_URL = os.getenv("DB_URL", "postgresql://sg:sg@localhost:5432/sg")

# Default tenant ID (can be overridden)
DEFAULT_TENANT_ID = os.getenv("TENANT_ID", "agribotsai-tenant-uuid")


def get_tenant_id(db: Session, tenant_slug: Optional[str] = None) -> Optional[uuid.UUID]:
    """Get tenant ID from database."""
    if tenant_slug:
        result = db.execute(
            text("SELECT id FROM tenants WHERE slug = :slug"),
            {"slug": tenant_slug}
        ).first()
        if result:
            return result[0]
    
    # Try to use DEFAULT_TENANT_ID as UUID
    try:
        return uuid.UUID(DEFAULT_TENANT_ID)
    except ValueError:
        # If not a valid UUID, try to find by slug
        if tenant_slug:
            result = db.execute(
                text("SELECT id FROM tenants WHERE slug = :slug"),
                {"slug": DEFAULT_TENANT_ID}
            ).first()
            if result:
                return result[0]
    
    return None


def seed_access_profiles(tenant_id: uuid.UUID, db: Session):
    """Seed default access profiles."""
    
    profiles = [
        {
            "name": "standard_employee",
            "display_name": "Standard Employee",
            "description": "Default access profile for standard employees. Includes basic application access.",
            "is_default": True,
            "is_system": False,
        },
        {
            "name": "developer",
            "display_name": "Developer",
            "description": "Access profile for software developers. Includes development tools and repositories.",
            "is_default": False,
            "is_system": False,
        },
        {
            "name": "manager",
            "display_name": "Manager",
            "description": "Access profile for managers. Includes team management tools and reporting.",
            "is_default": False,
            "is_system": False,
        },
        {
            "name": "executive",
            "display_name": "Executive",
            "description": "Access profile for executives. Includes high-level reporting and analytics.",
            "is_default": False,
            "is_system": False,
        },
        {
            "name": "contractor",
            "display_name": "Contractor",
            "description": "Access profile for contractors. Limited access to specific applications.",
            "is_default": False,
            "is_system": False,
        },
    ]
    
    created_count = 0
    skipped_count = 0
    
    for profile_data in profiles:
        # Check if profile already exists
        existing = db.execute(
            text("""
                SELECT id FROM access_profiles 
                WHERE tenant_id = :tenant_id AND name = :name
            """),
            {"tenant_id": str(tenant_id), "name": profile_data["name"]}
        ).first()
        
        if existing:
            print(f"  ⏭️  Skipping '{profile_data['display_name']}' (already exists)")
            skipped_count += 1
            continue
        
        # Insert profile
        profile_id = uuid.uuid4()
        db.execute(
            text("""
                INSERT INTO access_profiles 
                (id, tenant_id, name, display_name, description, is_default, is_system, created_at, updated_at)
                VALUES (:id, :tenant_id, :name, :display_name, :description, :is_default, :is_system, now(), now())
            """),
            {
                "id": str(profile_id),
                "tenant_id": str(tenant_id),
                "name": profile_data["name"],
                "display_name": profile_data["display_name"],
                "description": profile_data["description"],
                "is_default": profile_data["is_default"],
                "is_system": profile_data["is_system"],
            }
        )
        
        print(f"  ✅ Created '{profile_data['display_name']}' (ID: {profile_id})")
        created_count += 1
    
    db.commit()
    
    print(f"\n📊 Summary:")
    print(f"  Created: {created_count} profiles")
    print(f"  Skipped: {skipped_count} profiles (already exist)")
    
    return created_count


def main():
    """Main entry point."""
    print("=" * 60)
    print("Seed Access Profiles")
    print("=" * 60)
    print()
    
    # Create database connection
    engine = create_engine(DB_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Get tenant ID
        tenant_slug = os.getenv("TENANT_SLUG", "agribotsai")
        tenant_id = get_tenant_id(db, tenant_slug)
        
        if not tenant_id:
            print(f"❌ Error: Could not find tenant with slug '{tenant_slug}' or ID '{DEFAULT_TENANT_ID}'")
            print("   Please ensure the tenant exists in the database.")
            print("   You can set TENANT_ID or TENANT_SLUG environment variables.")
            sys.exit(1)
        
        print(f"📋 Tenant ID: {tenant_id}")
        print()
        
        # Seed profiles
        print("🌱 Seeding access profiles...")
        seed_access_profiles(tenant_id, db)
        
        print()
        print("✅ Access profiles seeded successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

