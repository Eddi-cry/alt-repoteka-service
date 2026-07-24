import asyncio
import logging
import sys
import os
from pathlib import Path

print("Run loader!!!")  

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
print(f"DB_HOST: {os.getenv('DB_HOST', 'NOT SET')}")  
print(f"DB_PASSWORD: {'***' if os.getenv('DB_PASSWORD') else 'NOT SET'}")  

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.loader.main import PackageLoader
    from src.config import Settings
    print("Import is successful")  
except Exception as e:
    print(f"Import error: {e}")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    print("Starting the download...")  
    settings = Settings()
    print(f"Connecting to the database: {settings.database_url}")  
    loader = PackageLoader(settings)
    loader.init_db()
    print("The database is initialized")  
    await loader.load_all_branches()
    print("The download is complete!")  

if __name__ == "__main__":
    print("Launching the main...")  
    asyncio.run(main())