"""
Database schema migration script.

This script applies the optimized schema with improved indexes and unique constraints.

Usage:
    python -m src.db.migrate

WARNING: This will drop and recreate all tables!
Make sure to backup your data before running this script.
"""

import asyncio
import sys

from sqlalchemy.ext.asyncio import create_async_engine

from src.config import Settings
from src.db.models import Base


async def migrate():
    """
    Drop all tables and recreate them with the new schema.

    WARNING: This will delete all data!
    """
    settings = Settings()

    # Create async engine
    database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(database_url, pool_pre_ping=True, echo=True)  # Show SQL statements

    print("⚠️  WARNING: This will DROP all existing tables and data!")
    print("⚠️  Make sure you have a backup before proceeding.")

    # Ask for confirmation
    response = input("\nType 'yes' to confirm migration: ")

    if response.lower() != "yes":
        print("Migration cancelled.")
        return

    print("\n🔄 Dropping existing tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    print("✅ Tables dropped.")

    print("\n🔄 Creating tables with new schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✅ Tables created with optimized schema!")

    print("\n📊 New schema includes:")
    print("  - UNIQUE constraint on (branch_id, name, arch, kind)")
    print("  - Optimized composite indexes for JOIN operations")
    print("  - Indexes for maintainer queries")
    print("  - Indexes for bulk package lookups")

    print("\n✅ Migration completed successfully!")
    print("\n💡 Next steps:")
    print("  1. Reload data: python -m src.cli.main load")
    print("  2. Test API: python -m src.cli.main serve")

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(migrate())
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
