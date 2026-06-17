"""
HealSense Backend - Development Server Startup Script
Run this to start the FastAPI server
"""
import sys
import os

# Add parent directory to path to enable imports
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    import uvicorn
    from api.config import get_settings
    
    settings = get_settings()
    
    print("\n" + "="*60)
    print("  🩺 HealSense Backend API")
    print("="*60)
    print(f"Environment: {settings.ENV}")
    print(f"Debug Mode: {settings.DEBUG}")
    print(f"Server: http://{settings.HOST}:{settings.PORT}")
    print(f"Docs: http://localhost:{settings.PORT}/api/docs")
    print(f"Health: http://localhost:{settings.PORT}/health")
    print("="*60 + "\n")
    
    uvicorn.run(
        "api.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
