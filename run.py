#!/usr/bin/env python3
"""
LLM Document Processing System Launcher
Handles environment setup and graceful startup
"""

import sys
import os
import subprocess
import signal
import time
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    return True

def check_virtual_environment():
    """Check if running in virtual environment"""
    return hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )

def create_directories():
    """Create necessary directories"""
    dirs = ['logs', 'data']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
    print("📁 Directories created/verified")

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = ['fastapi', 'uvicorn', 'pydantic', 'numpy']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True

def check_config_file():
    """Check if configuration file exists"""
    if not Path('.env').exists():
        if Path('env_example.txt').exists():
            print("⚙️  Creating .env from template...")
            with open('env_example.txt', 'r') as src, open('.env', 'w') as dst:
                dst.write(src.read())
            print("✅ .env file created. Please edit it with your settings.")
        else:
            print("⚠️  No .env file found. Using default configuration.")
    return True

def signal_handler(sig, frame):
    """Handle graceful shutdown"""
    print("\n⏹️  Shutting down gracefully...")
    sys.exit(0)

def main():
    """Main launcher function"""
    print("🚀 LLM Document Processing System Launcher")
    print("=" * 50)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Pre-flight checks
    if not check_python_version():
        sys.exit(1)
    
    print("✅ Python version check passed")
    
    if not check_virtual_environment():
        print("⚠️  Not running in virtual environment")
        print("   Consider running: source venv/bin/activate")
    else:
        print("✅ Virtual environment detected")
    
    create_directories()
    
    if not check_dependencies():
        print("\n🔧 To fix dependency issues:")
        print("   1. Activate virtual environment: source venv/bin/activate")
        print("   2. Install dependencies: pip install -r requirements.txt")
        print("   3. Run setup script: ./setup.sh")
        sys.exit(1)
    
    print("✅ Dependencies check passed")
    
    check_config_file()
    
    print("\n🏃 Starting system...")
    print("📖 API documentation will be available at: http://localhost:8000/docs")
    print("💡 System health check: http://localhost:8000/health")
    print("⏹️  Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        # Import and run the main application
        from main import app
        import uvicorn
        from src.config import get_settings
        
        settings = get_settings()
        
        # Start the server
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
            reload=settings.reload
        )
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure all dependencies are installed")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Startup error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
