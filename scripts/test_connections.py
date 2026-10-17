import asyncio
from sqlalchemy import text
from app.core.config import settings
from app.db.session import engine
from app.adapters.storage import S3StorageAdapter

async def main():
    print(f"=== Config loaded: app_name='{settings.app_name}', env='{settings.app_env}' ===")
    
    # Test DB
    print("Testing RDS database connection...")
    try:
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT 1"))
            print(f">>> RDS PostgreSQL OK: result = {res.scalar()}")
            
            # Check pgvector
            ext = await conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector'"))
            row = ext.fetchone()
            if row:
                print(f">>> pgvector extension is INSTALLED (v{row[0]})")
            else:
                print(">>> WARNING: pgvector extension NOT FOUND")
                
            # Check tables count
            for table in ["users", "categories", "courses", "chapters", "lessons", "system_settings"]:
                count = (await conn.execute(text(f"SELECT count(*) FROM {table}"))).scalar()
                print(f">>> Table '{table}': {count} rows")
    except Exception as e:
        print(f">>> RDS ERROR: {e}")
        
    # Test S3
    print("Testing S3 storage connection...")
    try:
        storage = S3StorageAdapter(settings)
        key = storage.check_connection()
        print(f">>> S3 Storage OK: check object verified")
    except Exception as e:
        print(f">>> S3 ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())
