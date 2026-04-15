import os, json
import pandas as pd
from datetime import datetime, timedelta, date

MONTHS_LIST = ['January','February','March','April','May','June',
               'July','August','September','October','November','December']

# =========================
# CONNECTION
# =========================

def _use_supabase():
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"))

def _sb():
    from supabase import create_client
    import streamlit as st
    @st.cache_resource
    def _client():
        return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    return _client()

def _sqlite():
    import db
    return db

# =========================
# INIT / SEED
# =========================

def init_db(buildings, schedule, devices):
    if not _use_supabase():
        return _sqlite().init_db(buildings, schedule, devices)
    from normalize_utils import clean_seed_payload
    sb = _sb()

    # Buildings
    existing = sb.table("buildings").select("bldg_num").limit(1).execute()
    if not existing.data:
        cleaned_b, cleaned_s, cleaned_d = clean_seed_payload(buildings, schedule, devices)
        seen = set()
        rows = []
        for b in cleaned_b:
            n = b.get('bldg_num')
            if not n or n in seen: continue
            seen.add(n)
            rows.append(b)
        for i in range(0, len(rows), 100):
            sb.table("buildings").insert(rows[i:i+100]).execute()

    # Schedule
    existing = sb.table("schedule").select("id").limit(1).execute()
    if not existing.data:
        _, cleaned_s, _ = clean_seed_payload(buildings, schedule, devices)
        for i in range(0, len(cleaned_s), 100):
            sb.table("schedule").insert(cleaned_s[i:i+100]).execute()

    # Devices
    existing = sb.table("devices").select("id").limit(1).execute()
    if not existing.data:
        _, _, cleaned_d = clean_seed_payload(buildings, schedule, devices)
        for i in range(0, len(cleaned_d), 500):
            sb.table("devices").insert(cleaned_d[i:i+500]).execute()

# =========================
# OVERDUE REFRESH
# =========================

def refresh_overdue_statuses():
    if not _use_supabase():
        return _sqlite().refresh_overdue_statuses()
    try:
        sb = _sb()
        cur_month = date.today().month
        all_rows = sb.table("schedule").select("id,month,status").execute().data or []
        overdue_ids = [
            r['id'] for r in all_rows
            if r.get('month') in MONTHS_LIST
            and MONTHS_LIST.index(r['month']) + 1 < cur_month
            and r.get('status') not in ('Complete', 'Construction')
        ]
        if overdue_ids:
            sb.table("schedule").update({"status": "Overdue"}).in_("id", overdue_ids).execute()
    except Exception as e:
        print("refresh_overdue_statuses error:", e)

# =========================
# BUILDINGS
# =========================

def get_buildings():
    if not _use_supabase():
        return _sqlite().get_buildings()
    try:
        res = _sb().table("buildings").select("*").order("bldg_num").execute()
        return res.data or []
    except:
        return []

def get_building(bldg_num):
    if not _use_supabase():
        return _sqlite().get_building(bldg_num)
    try:
        res = _sb().table("buildings").select("*").eq("bldg_num", str(bldg_num)).limit(1).execute()
        return (res.data or [{}])[0]
    except:
        return {}

def update_building(bldg_num, fields):
    if not _use_supabase():
        return _sqlite().update_building(bldg_num, fields)
    try:
        _sb().table("buildings").update(fields).eq("bldg_num", str(bldg_num)).execute()
    except Exception as e:
        print("update_building error:", e)

# =========================
# BUILDING IMAGES
# =========================

def get_building_image(bldg_num):
    if not _use_supabase():
        return _sqlite().get_building_image(bldg_num)
    try:
        res = _sb().table("building_images").select("image_data,image_ext")\
            .eq("bldg_num", str(bldg_num)).limit(1).execute()
        row = (res.data or [{}])[0]
        return row.get("image_data"), row.get("image_ext")
    except:
        return None, None

def save_building_image(bldg_num, image_bytes, ext='jpg'):
    if not _use_supabase():
        return _sqlite().save_building_image(bldg_num, image_bytes, ext)
    import base64
    try:
        sb = _sb()
        b64 = base64.b64encode(image_bytes).decode()
        existing = sb.table("building_images").select("bldg_num").eq("bldg_num", str(bldg_num)).execute()
        if existing.data:
            sb.table("building_images").update({"image_data": b64, "image_ext": ext})\
                .eq("bldg_num", str(bldg_num)).execute()
        else:
            sb.table("building_images").insert({"bldg_num": str(bldg_num), "image_data": b64, "image_ext": ext}).execute()
    except Exception as e:
        print("save_building_image error:", e)

def delete_building_image(bldg_num):
    if not _use_supabase():
        return _sqlite().delete_building_image(bldg_num)
    try:
        _sb().table("building_images").delete().eq("bldg_num", str(bldg_num)).execute()
    except Exception as e:
        print("delete_building_image error:", e)

# =========================
# SCHEDULE
# =========================

def get_schedule(month=None):
    if not _use_supabase():
        return _sqlite().get_schedule(month)
    try:
        q = _sb().table("schedule").select("*").order("inspection_date")
        if month and month != 'All':
            q = q.eq("month", month)
        return q.execute().data or []
    except:
        return []

def update_schedule_status(id, status, date_completed=None, notes=None, uploaded_cms=None):
    if not _use_supabase():
        return _sqlite().update_schedule_status(id, status, date_completed, notes, uploaded_cms)
    try:
        upd = {"status": status}
        if date_completed is not None: upd["date_completed"] = date_completed
        if notes is not None:          upd["notes"] = notes
        if uploaded_cms is not None:   upd["uploaded_cms"] = uploaded_cms
        _sb().table("schedule").update(upd).eq("id", id).execute()
    except Exception as e:
        print("update_schedule_status error:", e)

# =========================
# INSPECTIONS
# =========================

def get_inspections(bldg_num=None):
    if not _use_supabase():
        return _sqlite().get_inspections(bldg_num)
    try:
        q = _sb().table("inspections").select("*").order("inspection_date", desc=True)
        if bldg_num:
            q = q.eq("bldg_num", str(bldg_num))
        data = q.execute().data or []
        for row in data:
            if isinstance(row.get('deficiencies'), str):
                try: row['deficiencies'] = json.loads(row['deficiencies'])
                except: row['deficiencies'] = []
        return data
    except:
        return []

def save_inspection(data, deficiencies):
    if not _use_supabase():
        return _sqlite().save_inspection(data, deficiencies)
    try:
        row = dict(data)
        row['deficiencies'] = json.dumps(deficiencies)
        row['created_at'] = str(date.today())
        res = _sb().table("inspections").insert(row).execute()
        return res.data[0]['id']
    except Exception as e:
        print("save_inspection error:", e)
        return None

def save_device_results(insp_id, device_results):
    if not _use_supabase():
        return _sqlite().save_device_results(insp_id, device_results)
    try:
        _sb().table("inspections").update({"device_results": json.dumps(device_results)})\
            .eq("id", insp_id).execute()
    except Exception as e:
        print("save_device_results error:", e)

def get_device_results(insp_id):
    if not _use_supabase():
        return _sqlite().get_device_results(insp_id)
    try:
        res = _sb().table("inspections").select("device_results").eq("id", insp_id).limit(1).execute()
        row = (res.data or [{}])[0]
        val = row.get("device_results")
        if isinstance(val, str):
            return json.loads(val)
        return val if isinstance(val, dict) else {}
    except:
        return {}

# =========================
# DEVICES
# =========================

def get_devices_for_building(fp_name, bldg_name):
    if not _use_supabase():
        return _sqlite().get_devices_for_building(fp_name, bldg_name)
    try:
        sb = _sb()
        if fp_name:
            res = sb.table("devices").select("*").eq("building", str(fp_name).strip()).order("type").execute()
            if res.data: return res.data
        if bldg_name:
            res = sb.table("devices").select("*").ilike("building", f"%{str(bldg_name)[:8]}%").order("type").execute()
            if res.data: return res.data
        return []
    except:
        return []

def get_device_buildings():
    if not _use_supabase():
        return _sqlite().get_device_buildings()
    try:
        data = _sb().table("devices").select("building").execute().data or []
        return sorted(set(r['building'] for r in data if r.get('building')))
    except:
        return []

def search_devices(search, type_f, bldg_f):
    if not _use_supabase():
        return _sqlite().search_devices(search, type_f, bldg_f)
    try:
        sb = _sb()
        q = sb.table("devices").select("building,type,point,description")
        if type_f and type_f != 'All':
            q = q.eq("type", type_f)
        if bldg_f and bldg_f != 'All':
            q = q.eq("building", bldg_f)
        if search:
            q = q.ilike("building", f"%{search}%")
        data = q.order("building").order("type").limit(2000).execute().data or []
        if search and not data:
            data = sb.table("devices").select("building,type,point,description")\
                .ilike("description", f"%{search}%").order("building").limit(2000).execute().data or []
        return pd.DataFrame(data).rename(columns={
            'building': 'Building', 'type': 'Type',
            'point': 'Point', 'description': 'Description'
        }) if data else pd.DataFrame(columns=['Building','Type','Point','Description'])
    except:
        return pd.DataFrame(columns=['Building','Type','Point','Description'])

# =========================
# DASHBOARD
# =========================

def get_dashboard_stats():
    if not _use_supabase():
        return _sqlite().get_dashboard_stats()
    try:
        sb = _sb()
        buildings  = get_buildings()
        schedule   = get_schedule()
        inspections = sb.table("inspections").select("id").execute().data or []

        total      = len(buildings)
        scheduled  = len(schedule)
        complete   = sum(1 for s in schedule if s.get("status") == "Complete")
        overdue    = sum(1 for s in schedule if s.get("status") == "Overdue")
        init_dev   = sum(int(b.get('init_devices') or 0) for b in buildings)
        done_pct   = round(complete / scheduled * 100) if scheduled else 0

        month_counts = {}
        for r in schedule:
            m = r.get('month', '')
            if m not in month_counts:
                month_counts[m] = {'month': m, 'total': 0, 'complete': 0, 'overdue': 0}
            month_counts[m]['total'] += 1
            if r.get('status') == 'Complete': month_counts[m]['complete'] += 1
            if r.get('status') == 'Overdue':  month_counts[m]['overdue'] += 1

        dist_counts = {}
        for r in schedule:
            d = r.get('district', '')
            if d not in dist_counts:
                dist_counts[d] = {'district': d, 'cnt': 0, 'complete': 0}
            dist_counts[d]['cnt'] += 1
            if r.get('status') == 'Complete': dist_counts[d]['complete'] += 1

        return {
            "total_systems":   total,
            "total_buildings": total,
            "complete":        complete,
            "scheduled":       scheduled,
            "overdue":         overdue,
            "init_devices":    init_dev,
            "reports_saved":   len(inspections),
            "done_pct":        done_pct,
            "by_month":        list(month_counts.values()),
            "by_district":     list(dist_counts.values()),
        }
    except Exception as e:
        print("get_dashboard_stats error:", e)
        return {
            "total_systems": 0, "total_buildings": 0, "complete": 0,
            "scheduled": 0, "overdue": 0, "init_devices": 0,
            "reports_saved": 0, "done_pct": 0, "by_month": [], "by_district": [],
        }

def delete_inspection(insp_id):
    if not _use_supabase():
        return _sqlite().delete_inspection(insp_id)
    try:
        _sb().table("inspections").delete().eq("id", insp_id).execute()
    except Exception as e:
        print("delete_inspection error:", e)
