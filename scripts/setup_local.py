#!/usr/bin/env python3
"""Create local access keys once; never print or commit them."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / ".env"
if path.exists():
    print("Existing .env preserved.")
else:
    with path.open("x") as f:
        f.write(
            f"BINMAP_SURVEY_KEY={secrets.token_urlsafe(32)}\nBINMAP_REVIEW_KEY={secrets.token_urlsafe(32)}\n"
        )
    path.chmod(0o600)
    print(
        "Created .env with separate survey and review keys. Open it locally to sign in."
    )
(root / "data").mkdir(exist_ok=True)
