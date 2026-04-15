import os
import streamlit as st
from db_config import using_supabase, validate_db_config

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
# DASHBOARD
# -------------------------------

def get_dashboard_stats():
    if not _use_supabase():
        import db as _s
        return _s.get_dashboard_stats()

    sb = _sb()

    buildings = sb.table("buildings").select("id, init_devices, district").execute().data or []
    schedule = sb.table("schedule").select("id, month, district, status").execute().data or []
    inspections = sb.table("inspections").select("id").execute().data or []

    total_systems = len(buildings)
    total_devices = sum((b.get("init_devices") or 0) for b in buildings)

    scheduled = len(schedule)
    complete = sum(1 for r in schedule if (r.get("status") or "") == "Complete")
    overdue = sum(1 for r in schedule if (r.get("status") or "") == "Overdue")

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
def get_schedule(month=None):
    if not _use_supabase():
        import db as _s
        return _s.get_schedule(month)

    query = _sb().table("schedule").select("*").order("inspection_date", desc=False)

    if month and month != "All":
        query = query.eq("month", month)

    res = query.execute()
    return res.data or []