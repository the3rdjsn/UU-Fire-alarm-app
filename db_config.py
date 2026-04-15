import os

VALID_DB_MODES = {"supabase", "sqlite"}

def get_db_mode():
    mode = os.environ.get("DB_MODE", "sqlite").strip().lower()
    if mode not in VALID_DB_MODES:
        raise RuntimeError(f"Invalid DB_MODE='{mode}'")
    return mode

def using_supabase():
    return get_db_mode() == "supabase"

def validate_db_config():
    mode = get_db_mode()
    if mode == "supabase":
        if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_KEY"):
            raise RuntimeError("Missing Supabase env vars")
    return mode
