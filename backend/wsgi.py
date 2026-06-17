"""
WSGI entry point for HealSense Backend
"""
from api.app import app

if __name__ == "__main__":
    import uvicorn
    from api.config import get_settings
    
    settings = get_settings()
    uvicorn.run(
        "wsgi:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
