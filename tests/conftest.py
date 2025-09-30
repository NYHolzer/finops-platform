# tests/conftest.py
import sys
from pathlib import Path

# Add repo root to sys.path so `import platform_core` works
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
