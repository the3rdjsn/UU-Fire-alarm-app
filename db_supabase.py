import os
import base64
from datetime import datetime
import streamlit as st

from db_config import using_supabase, validate_db_config


# ──────────────────────────────────────────────────────────────────────────────
# CORE
# ──────────────────────────────────────────────────────────────────────────────

def _use_supabase():
    return using_supabase()


@st.cache_resource
def _get_supabase():
    validate_db_config()
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def _sb():
    return _get_supabase()


def _sqlite():
    import db as _s
    return _s


def _norm_bldg_num(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if "." in text:
        text = text.split(".")[0]
    return text


def _safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _safe_date_text(value):
    if not value:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "nan"}:
        return None
    return text[:10]


# ──────────────────────────────────────────────────────────────────────────────
# INIT / SEED
# ──────────────────────────────────────────────────────────────────────────────

def init_db(buildings, schedule, devices):
    if not _use_supabase():
        return _sqlite().init_db(buildings, schedule, devices)
    # Supabase tables are assumed to already exist.
    return True


# ──────────────────────────────────────────────────────────────────────────────
# BUILDINGS
# ──────────────────────────────────────────────────────────────────────────────

def get_buildings():
    if not _use_supabase():
        return _sqlite().get_buildings()

    res = (
        _sb()
        .table("buildings")
        .select("*")
        .order("bldg_num", desc=False)
        .execute()
    )
    return res.data or []


def get_building(bldg_num):
    if not _use_supabase():
        return _sqlite().get_building(bldg_num)

    target = _norm_bldg_num(bldg_num)
    res = (
        _sb()
        .table("buildings")
        .select("*")
        .eq("bldg_num", target)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def update_building(bldg_num, data):
    if not _use_supabase():
        return _sqlite().update_building(bldg_num, data)

    target = _norm_bldg_num(bldg_num)
    payload = dict(data)
    payload.pop("id", None)
    payload.pop("bldg_num", None)
    (
        _sb()
        .table("buildings")
        .update(payload)
        .eq("bldg_num", target)
        .execute()
    )
    return True


# ──────────────────────────────────────────────────────────────────────────────
# BUILDING IMAGES
# ──────────────────────────────────────────────────────────────────────────────

def get_building_image(bldg_num):
    if not _use_supabase():
        return _sqlite().get_building_image(bldg_num)

    target = _norm_bldg_num(bldg_num)

    # 1) Try Supabase table first
    try:
        res = (
            _sb()
            .table("building_images")
            .select("image_b64, image_ext")
            .eq("bldg_num", target)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if rows:
            row = rows[0]
            return row.get("image_b64"), row.get("image_ext", "png")
    except Exception:
        pass

    # 2) Fallback to local images folder
    base_dir = os.path.dirname(__file__)
    images_dir = os.path.join(base_dir, "images")
    for ext in ("png", "jpg", "jpeg", "webp"):
        path = os.path.join(images_dir, f"{target}.{ext}")
        if os.path.exists(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8"), ext

    return None, None


def save_building_image(bldg_num, image_bytes, image_ext="png"):
    if not _use_supabase():
        return _sqlite().save_building_image(bldg_num, image_bytes, image_ext)

    target = _norm_bldg_num(bldg_num)
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    # upsert-like behavior
    existing = (
        _sb()
        .table("building_images")
        .select("bldg_num")
        .eq("bldg_num", target)
        .limit(1)
        .execute()
    )
    if existing.data:
        (
            _sb()
            .table("building_images")
            .update({"image_b64": image_b64, "image_ext": image_ext})
            .eq("bldg_num", target)
            .execute()
        )
    else:
        (
            _sb()
            .table("building_images")
            .insert(
                {
                    "bldg_num": target,
                    "image_b64": image_b64,
                    "image_ext": image_ext,
                }
            )
            .execute()
        )
    return True


def remove_building_image(bldg_num):
    if not _use_supabase():
        return _sqlite().remove_building_image(bldg_num)

    target = _norm_bldg_num(bldg_num)

    try:
        (
            _sb()
            .table("building_images")
            .delete()
            .eq("bldg_num", target)
            .execute()
        )
    except Exception:
        pass

    # Also remove any local fallback image if present
    base_dir = os.path.dirname(__file__)
    images_dir = os.path.join(base_dir, "images")
    for ext in ("png", "jpg", "jpeg", "webp"):
        path = os.path.join(images_dir, f"{target}.{ext}")
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    return True


# ──────────────────────────────────────────────────────────────────────────────
# SCHEDULE
# ──────────────────────────────────────────────────────────────────────────────

def get_schedule(month=None):
    if not _use_supabase():
        return _sqlite().get_schedule(month)

    query = _sb().table("schedule").select("*").order("inspection_date", desc=False)
    if month and month != "All":
        query = query.eq("month", month)

    res = query.execute()
    return res.data or []


def update_schedule_status(row_id, status, completed_date=None, uploaded_cms=None, notes=None):
    if not _use_supabase():
        return _sqlite().update_schedule_status(row_id, status, completed_date, uploaded_cms)

    payload = {"status": status}
    if completed_date is not None:
        payload["date_completed"] = _safe_date_text(completed_date)
    if uploaded_cms is not None:
        payload["uploaded_cms"] = uploaded_cms
    if notes is not None:
        payload["notes"] = notes

    (
        _sb()
        .table("schedule")
        .update(payload)
        .eq("id", row_id)
        .execute()
    )
    return True


def update_schedule_notes(row_id, notes):
    if not _use_supabase():
        return _sqlite().update_schedule_notes(row_id, notes)

    (
        _sb()
        .table("schedule")
        .update({"notes": notes})
        .eq("id", row_id)
        .execute()
    )
    return True


# ──────────────────────────────────────────────────────────────────────────────
# DEVICES
# ──────────────────────────────────────────────────────────────────────────────

def get_devices(building=None):
    if not _use_supabase():
        return _sqlite().get_devices(building)

    query = _sb().table("devices").select("*")
    if building:
        query = query.eq("building", str(building))
    res = query.execute()
    return res.data or []


def get_device_inventory(building=None):
    return get_devices(building)


# ──────────────────────────────────────────────────────────────────────────────
# INSPECTIONS
# ──────────────────────────────────────────────────────────────────────────────

def get_inspections():
    if not _use_supabase():
        return _sqlite().get_inspections()

    res = _sb().table("inspections").select("*").order("inspection_date", desc=True).execute()
    return res.data or []


def save_inspection(data, deficiencies=None):
    if not _use_supabase():
        return _sqlite().save_inspection(data, deficiencies)

    payload = dict(data)
    if deficiencies is not None:
        payload["deficiencies"] = deficiencies

    res = _sb().table("inspections").insert(payload).execute()
    rows = res.data or []
    return rows[0]["id"] if rows else None


def update_inspection(insp_id, data, deficiencies=None):
    if not _use_supabase():
        return _sqlite().update_inspection(insp_id, data, deficiencies)

    payload = dict(data)
    if deficiencies is not None:
        payload["deficiencies"] = deficiencies

    (
        _sb()
        .table("inspections")
        .update(payload)
        .eq("id", insp_id)
        .execute()
    )
    return True


def delete_inspection(insp_id):
    if not _use_supabase():
        return _sqlite().delete_inspection(insp_id)

    (
        _sb()
        .table("inspections")
        .delete()
        .eq("id", insp_id)
        .execute()
    )
    return True


# ──────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────

def get_dashboard_stats():
    if not _use_supabase():
        return _sqlite().get_dashboard_stats()

    sb = _sb()

    buildings = sb.table("buildings").select("id, init_devices, district").execute().data or []
    schedule = sb.table("schedule").select("id, month, district, status").execute().data or []
    inspections = sb.table("inspections").select("id").execute().data or []

    total_systems = len(buildings)
    total_devices = sum((b.get("init_devices") or 0) for b in buildings)

    scheduled = len(schedule)
    complete = sum(1 for r in schedule if (r.get("status") or "").strip() == "Complete")
    overdue = sum(1 for r in schedule if (r.get("status") or "").strip() == "Overdue")

    month_order = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    by_month_map = {
        m: {"month": m, "total": 0, "done": 0, "complete": 0}
        for m in month_order
    }

    for row in schedule:
        month = row.get("month")
        status = (row.get("status") or "").strip()
        if month in by_month_map:
            by_month_map[month]["total"] += 1
            if status == "Complete":
                by_month_map[month]["done"] += 1
                by_month_map[month]["complete"] += 1

    by_month = [by_month_map[m] for m in month_order]

    district_counts = {}
    for b in buildings:
        district = (b.get("district") or "").strip()
        if district:
            district_counts[district] = district_counts.get(district, 0) + 1

    by_district = [
        {"district": district, "cnt": count}
        for district, count in sorted(district_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "total_systems": total_systems,
        "complete": complete,
        "scheduled": scheduled,
        "overdue": overdue,
        "init_devices": total_devices,
        "reports_saved": len(inspections),
        "by_month": by_month,
        "by_district": by_district,
    }


# ──────────────────────────────────────────────────────────────────────────────
# BACKWARD-COMPAT / NO-OPS
# ──────────────────────────────────────────────────────────────────────────────

def refresh_overdue_statuses():
    # Intentionally a no-op now so old app.py calls do not crash.
    return True