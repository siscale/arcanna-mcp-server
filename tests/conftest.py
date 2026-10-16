import os
import sys

os.environ.setdefault("ARCANNA_MANAGEMENT_API_KEY", "test-key")
os.environ.setdefault("ARCANNA_HOST", "http://arcanna.test:9666")
os.environ.setdefault("ARCANNA_AGENTS_HOST", "http://arcanna.test:9888")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
