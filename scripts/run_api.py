import sys
import os
import uvicorn


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api.main import app
from src.config import Settings

def main():
    settings = Settings()
    print(f"Launching the API server on http://{settings.api_host}:{settings.api_port}")
    print(f"Documentation: http://{settings.api_host}:{settings.api_port}/docs")
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        log_level="info"
    )

if __name__ == "__main__":
    main()