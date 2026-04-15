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
# INIT
# ─────────────────────────────────────────────────────────────

def init_db(buildings, schedule, devices):
    if not _use_supabase():
        return _sqlite().init_db(buildings, schedule, devices)
    # Supabase tables are assumed to already exist
    return True


# ─────────────────────────────────────────────────────────────
# BUILDINGS
# ─────────────────────────────────────────────────────────────

def get_buildings():
    if not _use_supabase():
        return _sqlite().get_buildings()

    res = _sb().table("buildings").select("*").execute()
    rows = res.data or []
    try:
        rows = sorted(rows, key=lambda r: str(r.get("name", "")))
    except Exception:
        pass
    return rows


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


def update_building(bldg_num, fields):
    if not _use_supabase():
        return _sqlite().update_building(bldg_num, fields)

    target = _norm(bldg_num)
    payload = dict(fields)
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


# ─────────────────────────────────────────────────────────────
# BUILDING IMAGES
# ─────────────────────────────────────────────────────────────

def get_building_image(bldg_num):
    if not _use_supabase():
        return _sqlite().get_building_image(bldg_num)

    target = _norm(bldg_num)

    # Try Supabase table first
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
    except Exception:
        pass

    # Fallback to local repo images folder
    img_dir = os.path.join(os.path.dirname(__file__), "images")
    for ext in ["jpg", "jpeg", "png", "webp", "JPG", "JPEG", "PNG", "WEBP"]:
        path = os.path.join(img_dir, f"{target}.{ext}")
        if os.path.exists(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode(), ext.lower()
    return None, None


def save_building_image(bldg_num, image_bytes, ext="jpg"):
    if not _use_supabase():
        return _sqlite().save_building_image(bldg_num, image_bytes, ext)

    target = _norm(bldg_num)
    image_b64 = base64.b64encode(image_bytes).decode()

    # Upsert-ish behavior
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
            .update({"image_b64": image_b64, "image_ext": ext})
            .eq("bldg_num", target)
            .execute()
        )
    else:
        (
            _sb()
            .table("building_images")
            .insert({
                "bldg_num": target,
                "image_b64": image_b64,
                "image_ext": ext,
            })
            .execute()
        )
    return True


def delete_building_image(bldg_num):
    if not _use_supabase():
        return _sqlite().delete_building_image(bldg_num)

    target = _norm(bldg_num)

    try:
        _sb().table("building_images").delete().eq("bldg_num", target).execute()
    except Exception:
        pass

    # Also remove local fallback image if present
    img_dir = os.path.join(os.path.dirname(__file__), "images")
    for ext in ["jpg", "jpeg", "png", "webp", "JPG", "JPEG", "PNG", "WEBP"]:
        path = os.path.join(img_dir, f"{target}.{ext}")
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
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
    rows = res.data or []

    month_order = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12
    }

    try:
        if month and month != "All":
            rows = sorted(rows, key=lambda r: (str(r.get("inspection_date") or "")))
        else:
            rows = sorted(
                rows,
                key=lambda r: (
                    month_order.get(r.get("month"), 99),
                    str(r.get("inspection_date") or "")
                )
            )
    except Exception:
        pass

    return rows


def update_schedule_status(sched_id, status, date_completed=None, notes=None, uploaded_cms=None):
    if not _use_supabase():
        return _sqlite().update_schedule_status(sched_id, status, date_completed, notes, uploaded_cms)

    payload = {"status": status}
    if date_completed is not None:
        payload["date_completed"] = str(date_completed)[:10] if date_completed else None
    if notes is not None:
        payload["notes"] = notes
    if uploaded_cms is not None:
        payload["uploaded_cms"] = uploaded_cms

    _sb().table("schedule").update(payload).eq("id", sched_id).execute()
    return True


def refresh_overdue_statuses():
    # No-op so old app.py calls do not crash and manual status edits are preserved
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


def get_devices_for_building(fp_name, bldg_name):
    if not _use_supabase():
        return _sqlite().get_devices_for_building(fp_name, bldg_name)

    values = []
    if fp_name:
        values.append(str(fp_name).strip())
    if bldg_name:
        values.append(str(bldg_name).strip())

    if not values:
        return []

    # Safer than OR string for messy values: fetch all and filter in Python
    res = _sb().table("devices").select("*").execute()
    rows = res.data or []

    filtered = [r for r in rows if str(r.get("building", "")).strip() in values]

    try:
        filtered = sorted(filtered, key=lambda r: (str(r.get("type", "")), str(r.get("point", ""))))
    except Exception:
        pass

    return filtered


def get_device_buildings():
    if not _use_supabase():
        return _sqlite().get_device_buildings()

    res = _sb().table("devices").select("building").execute()
    rows = res.data or []
    vals = sorted({str(r.get("building", "")).strip() for r in rows if r.get("building")})
    return vals


def search_devices(search, type_f, bldg_f):
    if not _use_supabase():
        return _sqlite().search_devices(search, type_f, bldg_f)

    import pandas as pd

    res = _sb().table("devices").select("building,type,point,description").execute()
    rows = res.data or []

    out = []
    search_l = (search or "").lower().strip()

    for r in rows:
        b = str(r.get("building", ""))
        t = str(r.get("type", ""))
        p = str(r.get("point", ""))
        d = str(r.get("description", ""))

        if type_f and type_f != "All" and t != type_f:
            continue
        if bldg_f and bldg_f != "All" and b != bldg_f:
            continue
        if search_l:
            blob = " ".join([b, t, p, d]).lower()
            if search_l not in blob:
                continue

        out.append([b, t, p, d])

    out.sort(key=lambda x: (x[0], x[1], x[2]))
    return pd.DataFrame(out, columns=["Building", "Type", "Point", "Description"])


# ─────────────────────────────────────────────────────────────
# INSPECTIONS
# ─────────────────────────────────────────────────────────────

def save_inspection(data, deficiencies):
    if not _use_supabase():
        return _sqlite().save_inspection(data, deficiencies)

    payload = dict(data)
    payload["deficiencies"] = deficiencies

    res = _sb().table("inspections").insert(payload).execute()
    rows = res.data or []
    insp_id = rows[0]["id"] if rows else None

    # Match SQLite behavior: mark related schedule complete
    bldg_num = _norm(data.get("bldg_num"))
    inspection_date = str(data.get("inspection_date") or "")[:10] if data.get("inspection_date") else None

    if bldg_num:
        (
            _sb()
            .table("schedule")
            .update({
                "status": "Complete",
                "date_completed": inspection_date
            })
            .eq("bldg_num", bldg_num)
            .execute()
        )

    return insp_id


def get_inspections(bldg_num=None):
    if not _use_supabase():
        return _sqlite().get_inspections(bldg_num)

    query = _sb().table("inspections").select("*")
    if bldg_num:
        query = query.eq("bldg_num", _norm(bldg_num))

    res = query.execute()
    rows = res.data or []

    try:
        if bldg_num:
            rows = sorted(rows, key=lambda r: str(r.get("inspection_date") or ""), reverse=True)
        else:
            rows = sorted(rows, key=lambda r: str(r.get("created_at") or ""), reverse=True)
    except Exception:
        pass

    return rows


def get_inspection(insp_id):
    if not _use_supabase():
        return _sqlite().get_inspection(insp_id)

    res = (
        _sb()
        .table("inspections")
        .select("*")
        .eq("id", insp_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def update_inspection(insp_id, data, deficiencies):
    if not _use_supabase():
        return _sqlite().update_inspection(insp_id, data, deficiencies)

    payload = dict(data)
    payload["deficiencies"] = deficiencies

    # Compute pct_tested like SQLite
    total = sum([(payload.get(f"{c}_total") or 0) for c in ["ps", "sd", "hd", "dd", "wf", "ts", "notif", "trans"]])
    tested = sum([(payload.get(f"{c}_tested") or 0) for c in ["ps", "sd", "hd", "dd", "wf", "ts", "notif", "trans"]])
    payload["pct_tested"] = round(tested / total * 100) if total > 0 else 0

    _sb().table("inspections").update(payload).eq("id", insp_id).execute()
    return True


def delete_inspection(insp_id):
    if not _use_supabase():
        return _sqlite().delete_inspection(insp_id)

    _sb().table("inspections").delete().eq("id", insp_id).execute()
    return True


def save_device_results(insp_id, device_results):
    if not _use_supabase():
        return _sqlite().save_device_results(insp_id, device_results)

    _sb().table("inspections").update({"device_results": device_results}).eq("id", insp_id).execute()
    return True


def get_device_results(insp_id):
    if not _use_supabase():
        return _sqlite().get_device_results(insp_id)

    res = (
        _sb()
        .table("inspections")
        .select("device_results")
        .eq("id", insp_id)
        .limit(1)
        .execute()
    )

    rows = res.data or []
    if not rows:
        return {}

    return rows[0].get("device_results") or {}


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
    total_devices = sum((b.get("init_devices") or 0) for b in buildings)

    scheduled = len(schedule)
    complete = sum(1 for r in schedule if r.get("status") == "Complete")
    overdue = sum(1 for r in schedule if r.get("status") == "Overdue")

    month_order = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    by_month_map = {m: {"month": m, "done": 0, "total": 0, "complete": 0} for m in month_order}
    for r in schedule:
        m = r.get("month")
        if m in by_month_map:
            by_month_map[m]["total"] += 1
            if r.get("status") == "Complete":
                by_month_map[m]["done"] += 1
                by_month_map[m]["complete"] += 1

    by_month = [by_month_map[m] for m in month_order]

    dist_counts = {}
    for r in schedule:
        d = str(r.get("district") or "").strip()
        if d:
            dist_counts[d] = dist_counts.get(d, 0) + 1

    by_district = [
        {"district": k, "cnt": v}
        for k, v in sorted(dist_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "total_systems": total_systems,
        "complete": complete,
        "scheduled": scheduled,
        "overdue": overdue,
        "init_devices": int(total_devices),
        "reports_saved": len(inspections),
        "by_month": by_month,
        "by_district": by_district,
    }