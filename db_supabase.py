import os
import base64
import streamlit as st
from db_config import using_supabase, validate_db_config


# ─────────────────────────────────────────────────────────────
# CORE
# ─────────────────────────────────────────────────────────────

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


def _norm(val):
    if val is None:
        return None
    return str(val).split(".")[0].strip()


# ─────────────────────────────────────────────────────────────
# BUILDINGS
# ─────────────────────────────────────────────────────────────

def get_buildings():
    if not _use_supabase():
        return _sqlite().get_buildings()

    res = _sb().table("buildings").select("*").execute()
    return res.data or []


def get_building(bldg_num):
    if not _use_supabase():
        return _sqlite().get_building(bldg_num)

    target = _norm(bldg_num)

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


# ─────────────────────────────────────────────────────────────
# BUILDING IMAGES
# ─────────────────────────────────────────────────────────────

def get_building_image(bldg_num):
    if not _use_supabase():
        return _sqlite().get_building_image(bldg_num)

    target = _norm(bldg_num)

    try:
        res = (
            _sb()
            .table("building_images")
            .select("*")
            .eq("bldg_num", target)
            .limit(1)
            .execute()
        )

        rows = res.data or []
        if rows:
            return rows[0].get("image_b64"), rows[0].get("image_ext", "png")
    except:
        pass

    return None, None


def save_building_image(bldg_num, image_bytes, ext="png"):
    if not _use_supabase():
        return _sqlite().save_building_image(bldg_num, image_bytes, ext)

    target = _norm(bldg_num)
    image_b64 = base64.b64encode(image_bytes).decode()

    _sb().table("building_images").upsert({
        "bldg_num": target,
        "image_b64": image_b64,
        "image_ext": ext
    }).execute()

    return True


# ─────────────────────────────────────────────────────────────
# SCHEDULE
# ─────────────────────────────────────────────────────────────

def get_schedule(month=None):
    if not _use_supabase():
        return _sqlite().get_schedule(month)

    query = _sb().table("schedule").select("*")

    if month and month != "All":
        query = query.eq("month", month)

    res = query.execute()
    return res.data or []


def update_schedule_status(row_id, status, completed_date=None, uploaded_cms=None, notes=None):
    if not _use_supabase():
        return _sqlite().update_schedule_status(row_id, status, completed_date)

    payload = {"status": status}

    if completed_date:
        payload["date_completed"] = str(completed_date)[:10]

    if uploaded_cms is not None:
        payload["uploaded_cms"] = uploaded_cms

    if notes is not None:
        payload["notes"] = notes

    _sb().table("schedule").update(payload).eq("id", row_id).execute()
    return True


# ─────────────────────────────────────────────────────────────
# DEVICES
# ─────────────────────────────────────────────────────────────

def get_devices(building=None):
    if not _use_supabase():
        return _sqlite().get_devices(building)

    query = _sb().table("devices").select("*")

    if building:
        query = query.eq("building", str(building))

    res = query.execute()
    return res.data or []


def get_devices_for_building(fp_name, building_name):
    if not _use_supabase():
        return _sqlite().get_devices_for_building(fp_name, building_name)

    query = _sb().table("devices").select("*")

    if building_name:
        query = query.eq("building", str(building_name))

    res = query.execute()
    rows = res.data or []

    # SAFE FILTER (no DB column dependency)
    if fp_name:
        fp = str(fp_name).lower()
        rows = [
            r for r in rows
            if fp in str(r.get("description", "")).lower()
            or fp in str(r.get("point", "")).lower()
        ]

    return rows


# ─────────────────────────────────────────────────────────────
# INSPECTIONS
# ─────────────────────────────────────────────────────────────

def get_inspections(bldg_num=None):
    if not _use_supabase():
        return _sqlite().get_inspections(bldg_num)

    query = _sb().table("inspections").select("*")

    if bldg_num:
        target = str(bldg_num).split(".")[0].strip()

        # Most likely correct column
        query = query.eq("bldg_num", target)

    res = query.execute()
    return res.data or []


# ─────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────

def get_dashboard_stats():
    if not _use_supabase():
        return _sqlite().get_dashboard_stats()

    buildings = _sb().table("buildings").select("*").execute().data or []
    schedule = _sb().table("schedule").select("*").execute().data or []
    inspections = _sb().table("inspections").select("*").execute().data or []

    total_systems = len(buildings)
    total_devices = sum(b.get("init_devices", 0) or 0 for b in buildings)

    scheduled = len(schedule)
    complete = sum(1 for r in schedule if r.get("status") == "Complete")
    overdue = sum(1 for r in schedule if r.get("status") == "Overdue")

    return {
        "total_systems": total_systems,
        "complete": complete,
        "scheduled": scheduled,
        "overdue": overdue,
        "init_devices": total_devices,
        "reports_saved": len(inspections),
        "by_month": [],
        "by_district": [],
    }


# ─────────────────────────────────────────────────────────────
# SAFE NO-OP
# ─────────────────────────────────────────────────────────────

def refresh_overdue_statuses():
    return True