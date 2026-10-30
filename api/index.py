import sys
import os

# Add parent directory to path so main.py and other modules can be imported seamlessly
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from main import app
