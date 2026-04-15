def normalize_text(val):
    if val is None:
        return None
    val = str(val).strip()
    if val.lower() in ("", "nan", "none"):
        return None
    return val

def clean_device_record(raw):
    if raw is None:
        return None

    if isinstance(raw, dict):
        return {
            "building": normalize_text(raw.get("building") or raw.get("Building")),
            "type": normalize_text(raw.get("type")),
            "point": normalize_text(raw.get("point")),
            "description": normalize_text(raw.get("description")),
        }

    if isinstance(raw, (list, tuple)):
        return {
            "building": normalize_text(raw[0]) if len(raw) > 0 else None,
            "type": normalize_text(raw[1]) if len(raw) > 1 else None,
            "point": normalize_text(raw[2]) if len(raw) > 2 else None,
            "description": normalize_text(raw[3]) if len(raw) > 3 else None,
        }

    return None
