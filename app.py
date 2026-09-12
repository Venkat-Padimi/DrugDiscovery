"""
Root entry point for the Streamlit Research Dashboard.
Run via: streamlit run app.py
"""
import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.ui.app import main

if __name__ == "__main__":
    main()
