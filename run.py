#!/usr/bin/env python3
"""
User Portal System Runner
Quick script to start the application with proper environment
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

# Configuration
VENV_NAME = "portal_env"
APP_FILE = "app.py"

def check_virtual_environment():
    """Check if virtual environment exists"""
    venv_path = Path(VENV_NAME)
    if not venv_path.exists():
        print(f"❌ Virtual environment '{VENV_NAME}' not found!")
        print("💡 Run 'python setup.py' first to create the environment.")
        return False
    return True

def get_python_executable():
    """Get the Python executable path in virtual environment"""
    if platform.system() == "Windows":
        return Path(VENV_NAME) / "Scripts" / "python.exe"
    else:
        return Path(VENV_NAME) / "bin" / "python"

def check_dependencies():
    """Check if required files exist"""
    required_files = [APP_FILE, "requirements.txt"]
    missing_files = []
    
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    return True

def run_application():
    """Run the Flask application"""
    python_exe = get_python_executable()
    
    if not python_exe.exists():
        print(f"❌ Python executable not found at {python_exe}")
        return False
    
    print("🚀 Starting User Portal System...")
    print("─" * 40)
    print(f"📁 Virtual Environment: {VENV_NAME}")
    print(f"🐍 Python: {python_exe}")
    print(f"📄 Application: {APP_FILE}")
    print("─" * 40)
    
    try:
        # Run the Flask application
        subprocess.run([str(python_exe), APP_FILE], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running application: {e}")
        return False
    except FileNotFoundError:
        print(f"❌ Could not find Python executable: {python_exe}")
        return False

def display_help():
    """Display help information"""
    print("User Portal System - Quick Runner")
    print("=" * 40)
    print("Usage: python run.py [option]")
    print("\nOptions:")
    print("  (no args)  - Start the application")
    print("  --help     - Show this help message")
    print("  --check    - Check system requirements")
    print("  --info     - Show application information")
    print("\nFirst time setup:")
    print("  1. python setup.py")
    print("  2. python run.py")

def check_system():
    """Check system requirements and status"""
    print("🔍 System Check")
    print("=" * 30)
    
    # Check virtual environment
    if check_virtual_environment():
        print("✅ Virtual environment found")
    else:
        print("❌ Virtual environment missing")
        return False
    
    # Check dependencies
    if check_dependencies():
        print("✅ Required files found")
    else:
        print("❌ Missing required files")
        return False
    
    # Check Python executable
    python_exe = get_python_executable()
    if python_exe.exists():
        print("✅ Python executable found")
    else:
        print("❌ Python executable missing")
        return False
    
    # Check database (optional)
    if Path("user_portal.db").exists():
        print("✅ Database file exists")
    else:
        print("⚠️  Database will be created on first run")
    
    print("\n🎉 System check passed!")
    return True

def show_info():
    """Show application information"""
    print("ℹ️  User Portal System Information")
    print("=" * 40)
    print("Name: User Portal System")
    print("Framework: Flask (Python)")
    print("Database: SQLite")
    print("Virtual Environment: portal_env")
    print("Default Port: 5000")
    print("Features:")
    print("  • User authentication")
    print("  • Success popup modal")
    print("  • Responsive design")
    print("  • RESTful API")
    print("  • SQLite database")
    print("  • Input validation")

def main():
    """Main function"""
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg in ['--help', '-h', 'help']:
            display_help()
            return
        elif arg in ['--check', '-c', 'check']:
            check_system()
            return
        elif arg in ['--info', '-i', 'info']:
            show_info()
            return
        else:
            print(f"❌ Unknown option: {arg}")
            print("💡 Use --help for available options")
            return
    
    # Default behavior - run the application
    if not check_virtual_environment():
        return
    
    if not check_dependencies():
        return
    
    run_application()

if __name__ == "__main__":
    main()