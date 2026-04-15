import os
import streamlit as st
from datetime import datetime, timedelta

# ✅ FIX: proper import
from db_config import using_supabase, validate_db_config

# -------------------------------
# Helpers
# -------------------------------

def _use_supabase():
    return using_supabase()

@st.cache_resource
def _get_supabase():
    validate_db_config()
    from supabase import create_client
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)

def _sb():
    return _get_supabase()

# -------------------------------
# INIT DB
# -------------------------------

def init_db(buildings, schedule, devices):
    if not _use_supabase():
        import db as _s
        return _s.init_db(buildings, schedule, devices)

    # Supabase assumes tables already exist
    return True

# -------------------------------
# SCHEDULE
# -------------------------------

def update_schedule_status(row_id, status, completed_date=None, uploaded_cms=None):
    if not _use_supabase():
        import db as _s
        return _s.update_schedule_status(row_id, status, completed_date, uploaded_cms)

    data = {
        "status": status,
        "date_completed": completed_date,
        "uploaded_cms": uploaded_cms,
    }

    _sb().table("schedule").update(data).eq("id", row_id).execute()

# -------------------------------
# INSPECTIONS
# -------------------------------

def get_inspections():
    if not _use_supabase():
        import db as _s
        return _s.get_inspections()

    res = _sb().table("inspections").select("*").execute()
    return res.data if res.data else []

def delete_inspection(insp_id):
    if not _use_supabase():
        import db as _s
        return _s.delete_inspection(insp_id)

    _sb().table("inspections").delete().eq("id", insp_id).execute()

# -------------------------------
# DASHBOARD
# -------------------------------

def get_dashboard_stats():
    if not _use_supabase():
        import db as _s
        return _s.get_dashboard_stats()

    sb = _sb()

    buildings = sb.table("buildings").select("id, init_devices").execute().data or []
    schedule = sb.table("schedule").select("*").execute().data or []
    inspections = sb.table("inspections").select("id").execute().data or []

    total_systems = len(buildings)
    total_devices = sum(b.get("init_devices") or 0 for b in buildings)

    complete = sum(1 for r in schedule if r.get("status") == "Complete")
    overdue = sum(1 for r in schedule if r.get("status") == "Overdue")

    return {
        "total_systems": total_systems,
        "inspections_complete": complete,
        "overdue": overdue,
        "init_devices": total_devices,
        "reports_saved": len(inspections),
    }