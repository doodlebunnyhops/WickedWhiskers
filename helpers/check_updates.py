#!/usr/bin/env python3
"""
Script to check for updates to packages in requirements.txt
"""
import subprocess
import sys
import re
from typing import List, Dict, Tuple

def parse_requirements(file_path: str) -> List[Tuple[str, str, str]]:
    """Parse requirements.txt and return list of (package, version, operator) tuples"""
    requirements = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Handle different version specifiers (==, >=, <=, etc.)
                    match = re.match(r'([a-zA-Z0-9_.-]+)(==|>=|<=|>|<|~=)([0-9.]+)', line)
                    if match:
                        package, operator, version = match.groups()
                        requirements.append((package, version, operator))
                    else:
                        # Handle packages without version specifiers
                        if re.match(r'^[a-zA-Z0-9_.-]+$', line):
                            requirements.append((line, "latest", ""))
    except FileNotFoundError:
        print(f"Error: {file_path} not found")
        sys.exit(1)
    return requirements

def get_latest_version(package: str) -> str:
    """Get the latest version of a package from PyPI"""
    try:
        # First try using pip index
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'index', 'versions', package],
            capture_output=True,
            text=True,
            check=True
        )
        # Parse output to get available versions
        for line in result.stdout.split('\n'):
            if 'Available versions:' in line:
                versions = line.split('Available versions:')[1].strip()
                # Get the first (latest) version
                latest = versions.split(',')[0].strip()
                return latest
    except subprocess.CalledProcessError:
        pass
    
    # Fallback: try using pip search with JSON output
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'search', package],
            capture_output=True,
            text=True,
            check=True
        )
        # This command is deprecated but might work
        for line in result.stdout.split('\n'):
            if line.startswith(f"{package} ("):
                version = line.split('(')[1].split(')')[0]
                return version
    except subprocess.CalledProcessError:
        pass
    
    # Another fallback: use requests to check PyPI API
    try:
        import json
        import urllib.request
        
        url = f"https://pypi.org/pypi/{package}/json"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())
            return data['info']['version']
    except Exception:
        pass
    
    return "Unknown"

def check_outdated_packages() -> Dict[str, Dict[str, str]]:
    """Get outdated packages using pip list --outdated"""
    outdated = {}
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list', '--outdated', '--format=json'],
            capture_output=True,
            text=True,
            check=True
        )
        import json
        outdated_list = json.loads(result.stdout)
        for package in outdated_list:
            outdated[package['name']] = {
                'current': package['version'],
                'latest': package['latest_version']
            }
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        # Fallback to text parsing
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list', '--outdated'],
            capture_output=True,
            text=True
        )
        lines = result.stdout.split('\n')[2:]  # Skip header
        for line in lines:
            if line.strip():
                parts = line.split()
                if len(parts) >= 3:
                    package_name = parts[0]
                    current_version = parts[1]
                    latest_version = parts[2]
                    outdated[package_name] = {
                        'current': current_version,
                        'latest': latest_version
                    }
    return outdated

def main():
    requirements_file = 'requirements.txt'
    print(f"Checking for updates in {requirements_file}...")
    print("=" * 60)
    
    # Parse requirements
    requirements = parse_requirements(requirements_file)
    
    if not requirements:
        print("No requirements found or file is empty")
        return
    
    # Get outdated packages
    outdated_packages = check_outdated_packages()
    
    # Check each requirement
    updates_available = False
    for package, version, operator in requirements:
        print(f"\n📦 {package}")
        print(f"   Current: {version} ({operator})")
        
        # Check if this package is in the outdated list
        if package in outdated_packages:
            latest = outdated_packages[package]['latest']
            print(f"   Latest:  {latest} ✨")
            if latest != version:
                print(f"   Status:  UPDATE AVAILABLE! 🚀")
                updates_available = True
            else:
                print(f"   Status:  Up to date ✅")
        else:
            # Package not in outdated list, check if it's actually up to date
            # or if we need to query for the latest version
            if version == "latest":
                # Package without version specifier
                latest = get_latest_version(package)
                print(f"   Latest:  {latest} ✨")
                print(f"   Status:  No version specified in requirements")
            else:
                # Package has version but not in outdated list - likely up to date
                # But let's double-check by getting the latest version
                latest = get_latest_version(package)
                if latest != "Unknown" and latest != version:
                    print(f"   Latest:  {latest} ✨")
                    print(f"   Status:  UPDATE AVAILABLE! 🚀")
                    updates_available = True
                else:
                    print(f"   Status:  Up to date ✅")
    
    print("\n" + "=" * 60)
    if updates_available:
        print("🎯 Updates are available! Run the following commands to update:")
        print("\n# Update specific packages:")
        for package, version, operator in requirements:
            if package in outdated_packages:
                latest = outdated_packages[package]['latest']
                if latest != version:
                    print(f"pip install {package}=={latest}")
            else:
                # Check if package needs update
                latest = get_latest_version(package)
                if latest != "Unknown" and latest != version and version != "latest":
                    print(f"pip install {package}=={latest}")
        
        print("\n# Or update all packages:")
        print("pip install --upgrade -r requirements.txt")
        
        print("\n# To update requirements.txt with new versions:")
        print("pip freeze > requirements.txt")
    else:
        print("🎉 All packages are up to date!")

if __name__ == "__main__":
    main()
