import os
import re

ROUTERS_DIR = "interfaces/api/routers"

for filename in os.listdir(ROUTERS_DIR):
    if not filename.endswith(".py") or filename == "auth.py" or filename == "__init__.py":
        continue
    filepath = os.path.join(ROUTERS_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Replace DEMO_USER_ID or DEFAULT_USER_ID with imports
    content = re.sub(
        r'([A-Z_]+_USER_ID\s*=\s*"[^"]+")',
        r'from interfaces.api.dependencies.auth import get_current_user_id',
        content
    )

    # 2. Inject user_id into route signatures (those having session: AsyncSession)
    # We find definitions that look like async def name(..., session: AsyncSession = Depends(get_session), ...)
    def inject_dep(match):
        sig = match.group(0)
        if "user_id: str = Depends(get_current_user_id)" not in sig:
            # Insert before session: AsyncSession
            return sig.replace("session: AsyncSession", "user_id: str = Depends(get_current_user_id),\n    session: AsyncSession")
        return sig

    content = re.sub(r'async def [a-zA-Z0-9_]+\([^)]*session:\s*AsyncSession[^)]*\)[^:]*:', inject_dep, content)

    # 3. Replace usage of the constant with `user_id`
    content = re.sub(r'\b(DEMO_USER_ID|DEFAULT_USER_ID)\b', 'user_id', content)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Refactored {filename}")
