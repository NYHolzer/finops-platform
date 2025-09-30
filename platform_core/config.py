import os

from dotenv import load_dotenv

# Load variables from .env (repo root)
load_dotenv()

# === SEC settings ===
SEC_CONTACT_EMAIL = os.getenv("SEC_CONTACT_EMAIL", "change-me@example.com")
SEC_USER_AGENT = f"FinOpsPlatform/0.1 (Contact: {SEC_CONTACT_EMAIL})"

# === Project defaults ===
ANALYST_DEFAULT_TICKER = os.getenv("ANALYST_DEFAULT_TICKER", "AAPL")

# === Navigation modules (keep in sync with repo) ===
NAV_MODULES = ("analyst", "trader")
