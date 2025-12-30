#!/usr/bin/env python3
"""
Script to create an admin user for the ANHA application.
Run with: python scripts/create_admin.py
"""
import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import engine, Base
from app.models.user import User, Role
from app.core.security import hash_password


async def create_admin():
    """Create the admin user if it doesn't exist."""
    
    # Admin credentials
    ADMIN_EMAIL = "admin@email.com"
    ADMIN_PASSWORD = "admin12345"
    ADMIN_NAME = "مدير النظام"
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        # Check if admin exists
        result = await session.execute(
            select(User).where(User.email == ADMIN_EMAIL)
        )
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            print(f"✅ Admin user already exists: {ADMIN_EMAIL}")
            print(f"   Role: {existing_admin.role.value}")
            return
        
        # Create admin user
        admin = User(
            email=ADMIN_EMAIL,
            full_name=ADMIN_NAME,
            phone="0500000000",
            hashed_password=hash_password(ADMIN_PASSWORD),
            role=Role.admin,
            is_active=True,
        )
        
        session.add(admin)
        await session.commit()
        
        print("=" * 50)
        print("🛡️  ADMIN USER CREATED SUCCESSFULLY")
        print("=" * 50)
        print(f"📧 Email:    {ADMIN_EMAIL}")
        print(f"🔑 Password: {ADMIN_PASSWORD}")
        print(f"👤 Name:     {ADMIN_NAME}")
        print(f"🎭 Role:     admin")
        print("=" * 50)
        print("\n⚠️  Important: Change the password after first login!")


if __name__ == "__main__":
    print("\n🚀 Creating admin user...\n")
    asyncio.run(create_admin())
