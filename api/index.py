import sys
import os

# Add parent directory to path so we can import serve.py and other modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from serve import app as app
