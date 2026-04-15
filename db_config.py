import os

VALID_DB_MODES = {"supabase", "sqlite"}

def get_db_mode():
    mode = os.environ.get("DB_MODE", "sqlite").strip().lower()
    if mode not in VALID_DB_MODES:
        raise RuntimeError(
            f"Invalid DB_MODE={mode!r}. Expected one of: {', '.join(sorted(VALID_DB_MODES))}"
        )
    return mode

def using_supabase():
    return get_db_mode() == "supabase"

def validate_db_config():
    mode = get_db_mode()
    if mode == "supabase":
        missing = [k for k in ("SUPABASE_URL", "SUPABASE_KEY") if not os.environ.get(k)]
        if missing:
            raise RuntimeError(
                "DB_MODE is 'supabase' but these env vars are missing: " + ", ".join(missing)
            )
    return mode
