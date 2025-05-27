#!/usr/bin/env python3
"""
User Portal System Setup Script
Automatically creates virtual environment and installs dependencies
"""

import os
import sys
import subprocess
import platform

# Project configuration
PROJECT_NAME = "user_portal_system"
VENV_NAME = "portal_env"
PYTHON_VERSION = "python3"

def run_command(command, description):
    """Run a shell command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully!")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}:")
        print(f"   Command: {command}")
        print(f"   Error: {e.stderr}")
        return None

def check_python():
    """Check if Python is installed"""
    try:
        result = subprocess.run([PYTHON_VERSION, "--version"], capture_output=True, text=True)
        version = result.stdout.strip()
        print(f"✅ Found {version}")
        return True
    except FileNotFoundError:
        print(f"❌ {PYTHON_VERSION} not found. Please install Python 3.7 or higher.")
        return False

def create_virtual_environment():
    """Create and activate virtual environment"""
    if os.path.exists(VENV_NAME):
        print(f"⚠️  Virtual environment '{VENV_NAME}' already exists.")
        return True
    
    command = f"{PYTHON_VERSION} -m venv {VENV_NAME}"
    return run_command(command, f"Creating virtual environment '{VENV_NAME}'")

def get_activation_command():
    """Get the command to activate virtual environment based on OS"""
    if platform.system() == "Windows":
        return f"{VENV_NAME}\\Scripts\\activate"
    else:
        return f"source {VENV_NAME}/bin/activate"

def install_dependencies():
    """Install dependencies from requirements.txt"""
    pip_path = os.path.join(VENV_NAME, "Scripts", "pip") if platform.system() == "Windows" else os.path.join(VENV_NAME, "bin", "pip")
    
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt not found!")
        return False
    
    command = f"{pip_path} install -r requirements.txt"
    return run_command(command, "Installing dependencies")

def create_project_structure():
    """Create necessary project directories"""
    directories = ["templates", "static", "logs"]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"📁 Created directory: {directory}")

def display_instructions():
    """Display setup completion instructions"""
    activation_cmd = get_activation_command()
    
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETED SUCCESSFULLY!")
    print("="*60)
    print(f"📁 Project: {PROJECT_NAME}")
    print(f"🐍 Virtual Environment: {VENV_NAME}")
    print(f"🌐 Server: Flask (Python)")
    print(f"💾 Database: SQLite")
    
    print("\n📋 TO RUN THE APPLICATION:")
    print("─"*30)
    print(f"1. Activate virtual environment:")
    print(f"   {activation_cmd}")
    print(f"\n2. Start the server:")
    print(f"   python app.py")
    print(f"\n3. Open your browser:")
    print(f"   http://localhost:5000")
    
    print("\n🧪 SAMPLE TEST ACCOUNTS:")
    print("─"*30)
    print("Email: alex.johnson@email.com    | Phone: +1 555-0101")
    print("Email: maria.garcia@email.com    | Phone: +1 555-0102")
    print("Email: david.chen@email.com      | Phone: +1 555-0103")
    print("Email: sarah.williams@email.com  | Phone: +1 555-0104")
    print("Email: michael.brown@email.com   | Phone: +1 555-0105")
    
    print("\n🛠️  PROJECT STRUCTURE:")
    print("─"*30)
    print("user_portal_system/")
    print("├── portal_env/          # Virtual environment")
    print("├── app.py              # Main Flask application")
    print("├── requirements.txt    # Dependencies")
    print("├── setup.py           # This setup script")
    print("├── user_portal.db     # SQLite database (auto-created)")
    print("├── templates/         # HTML templates (optional)")
    print("├── static/           # CSS/JS files (optional)")
    print("└── logs/             # Application logs")
    
    print("\n🔧 ADDITIONAL COMMANDS:")
    print("─"*30)
    print("• Deactivate virtual environment: deactivate")
    print("• View all users: GET /api/users")
    print("• Create new user: POST /api/users")
    print("• Delete user: DELETE /api/users/<id>")
    
    print("\n💡 DEVELOPMENT TIPS:")
    print("─"*30)
    print("• Flask runs in debug mode (auto-reload enabled)")
    print("• Database file created automatically on first run")
    print("• CORS enabled for API testing")
    print("• All routes logged to console")
    
    print("\n" + "="*60)

def main():
    """Main setup function"""
    print("🚀 Starting User Portal System Setup...")
    print("="*50)
    
    # Check Python installation
    if not check_python():
        sys.exit(1)
    
    # Create virtual environment
    if not create_virtual_environment():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Create project structure
    create_project_structure()
    
    # Display completion instructions
    display_instructions()

if __name__ == "__main__":
    main()