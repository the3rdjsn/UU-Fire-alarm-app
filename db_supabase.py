import os
from datetime import datetime, timedelta
from supabase import create_client

# =========================
# INIT
# =========================

def _sb():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)


def _use_supabase():
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"))


def _sqlite():
    import db
    return db


# =========================
# BUILDINGS
# =========================

def get_buildings():
    if not _use_supabase():
        return _sqlite().get_buildings()

    try:
        res = _sb().table("buildings").select("*").execute()
        return res.data or []
    except:
        return []


def get_building(num):
    if not _use_supabase():
        return _sqlite().get_building(num)

    try:
        res = _sb().table("buildings").select("*").eq("num", num).limit(1).execute()
        return (res.data or [{}])[0]
    except:
        return {}


# =========================
# BUILDING IMAGE
# =========================

def get_building_image(num):
    if not _use_supabase():
        return _sqlite().get_building_image(num)

    try:
        res = (
            _sb()
            .table("buildings")
            .select("image_base64, image_ext")
            .eq("num", num)
            .limit(1)
            .execute()
        )
        row = (res.data or [{}])[0]
        return row.get("image_base64"), row.get("image_ext")
    except:
        return None, None


# =========================
# DEVICES (FOCALPOINT)
# =========================

def get_devices_for_building(fp_name, bldg_name):
    if not _use_supabase():
        return _sqlite().get_devices_for_building(fp_name, bldg_name)

    try:
        res = _sb().table("devices").select("*").execute()
        rows = res.data or []

        values = []
        if fp_name:
            values.append(str(fp_name).strip())
        if bldg_name:
            values.append(str(bldg_name).strip())

        if not values:
            return []

        out = [
            r for r in rows
            if str(r.get("building", "")).strip() in values
        ]

        try:
            out = sorted(out, key=lambda r: (str(r.get("type", "")), str(r.get("point", ""))))
        except:
            pass

        return out

    except:
        return []


# =========================
# INSPECTIONS
# =========================

def get_inspections(bldg_num):
    if not _use_supabase():
        return _sqlite().get_inspections(bldg_num)

    try:
        res = (
            _sb()
            .table("inspections")
            .select("*")
            .eq("building_num", bldg_num)
            .order("date", desc=True)
            .execute()
        )
        return res.data or []
    except:
        return []


def save_inspection(data, deficiencies):
    if not _use_supabase():
        return _sqlite().save_inspection(data, deficiencies)

    try:
        data = dict(data)
        data["device_results"] = data.get("device_results", {})

        res = _sb().table("inspections").insert(data).execute()
        insp_id = res.data[0]["id"]

        # save deficiencies
        for d in deficiencies:
            d["inspection_id"] = insp_id
            _sb().table("deficiencies").insert(d).execute()

        return insp_id
    except Exception as e:
        print("SAVE ERROR:", e)
        return None


def get_device_results(insp_id):
    if not _use_supabase():
        return _sqlite().get_device_results(insp_id)

    try:
        res = (
            _sb()
            .table("inspections")
            .select("device_results")
            .eq("id", insp_id)
            .limit(1)
            .execute()
        )
        row = (res.data or [{}])[0]
        val = row.get("device_results")
        return val if isinstance(val, dict) else {}
    except:
        return {}


# =========================
# SCHEDULE
# =========================

def get_schedule():
    if not _use_supabase():
        return _sqlite().get_schedule()

    try:
        res = _sb().table("schedule").select("*").execute()
        return res.data or []
    except:
        return []


def update_schedule_status(id, status):
    if not _use_supabase():
        return _sqlite().update_schedule_status(id, status)

    try:
        _sb().table("schedule").update({"status": status}).eq("id", id).execute()
    except:
        pass


# =========================
# OVERDUE LOGIC (1 YEAR)
# =========================

def refresh_overdue_statuses():
    if not _use_supabase():
        return _sqlite().refresh_overdue_statuses()

    try:
        rows = get_schedule()
        now = datetime.now()

        for r in rows:
            d = r.get("inspection_date")
            if not d:
                continue

            try:
                dt = datetime.fromisoformat(d)
            except:
                continue

            if now - dt > timedelta(days=365):
                _sb().table("schedule").update({"status": "Overdue"}).eq("id", r["id"]).execute()
    except:
        pass


# =========================
# DASHBOARD
# =========================

def get_dashboard_stats():
    if not _use_supabase():
        return _sqlite().get_dashboard_stats()

    try:
        schedule = get_schedule()
        inspections = _sb().table("inspections").select("*").execute().data or []
        buildings = get_buildings()

        total = len(buildings)
        complete = sum(1 for s in schedule if s.get("status") == "Complete")
        scheduled = len(schedule)

        overdue = 0
        now = datetime.now()
        for s in schedule:
            try:
                d = datetime.fromisoformat(s.get("inspection_date"))
                if now - d > timedelta(days=365):
                    overdue += 1
            except:
                pass

        return {
            "total": total,
            "complete": complete,
            "scheduled": scheduled,
            "overdue": overdue,
            "by_month": [],
            "by_district": []
        }

    except:
        return {
            "total": 0,
            "complete": 0,
            "scheduled": 0,
            "overdue": 0,
            "by_month": [],
            "by_district": []
        }