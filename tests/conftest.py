"""
Pytest configuration for test directory.
"""
import os
import sys

# Ensure the project root is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Create screenshot directories if they don't exist
os.makedirs(os.path.join(project_root, 'reports', 'screenshots', 'pass'), exist_ok=True)
os.makedirs(os.path.join(project_root, 'reports', 'screenshots', 'fail'), exist_ok=True)
os.makedirs(os.path.join(project_root, 'reports'), exist_ok=True)
