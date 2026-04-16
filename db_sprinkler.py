"""
db_sprinkler.py  —  Supabase backend for the sprinkler inspection module.
All functions fall back to SQLite if SUPABASE_URL/KEY are not set.
"""
import os, json
import pandas as pd
from datetime import date

# ── helpers ──────────────────────────────────────────────────────────────────

def _use_supabase():
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"))

def _sb():
    from supabase import create_client
    import streamlit as st
    @st.cache_resource
    def _client():
        return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    return _client()

# ── buildings ─────────────────────────────────────────────────────────────────

def get_sprinkler_buildings():
    if not _use_supabase(): return []
    try:
        res = _sb().table("sprinkler_buildings").select("*").order("bldg_num").execute()
        return res.data or []
    except Exception as e:
        print("get_sprinkler_buildings error:", e); return []

# ── inventory ─────────────────────────────────────────────────────────────────

def get_inventory_for_building(bldg_num):
    """Return all riser components for a building."""
    if not _use_supabase(): return []
    try:
        res = (_sb().table("sprinkler_inventory")
               .select("*").eq("bldg_num", str(bldg_num))
               .order("system_type").order("component").execute())
        return res.data or []
    except Exception as e:
        print("get_inventory_for_building error:", e); return []

# ── NFPA 25 standards ─────────────────────────────────────────────────────────

def get_nfpa25_standards():
    """Return all NFPA 25 standards (cached)."""
    if not _use_supabase(): return []
    try:
        import streamlit as st
        @st.cache_data(ttl=3600)
        def _load():
            res = _sb().table("nfpa25_standards").select("*").execute()
            return res.data or []
        return _load()
    except Exception as e:
        print("get_nfpa25_standards error:", e); return []

def get_inspection_items_for_building(bldg_num, freq_type):
    """
    Cross-reference building inventory against NFPA 25 standards
    for the chosen frequency. Returns list of dicts ready for the
    inspection form.
    freq_type: 'Quarterly' | 'Semiannual' | 'Annual' | '3-Year' | '5-Year'
    """
    inventory = get_inventory_for_building(bldg_num)
    standards = get_nfpa25_standards()

    # Map frequency selection → NFPA frequency strings
    FREQ_MAP = {
        'Quarterly':  ['Quarterly (Winter, Spring, Summer, Fall)'],
        'Semiannual': ['Semiannually (Spring, Fall)'],
        'Annual':     ['Annually (Winter)', 'Annually (Spring)',
                       'Annually (Summer)', 'Annually (Fall)'],
        '3-Year':     ['3 year'],
        '5-Year':     ['5 year'],
    }
    target_freqs = FREQ_MAP.get(freq_type, [])

    # Filter standards to target frequency
    std_lookup = {}  # component -> [standard rows]
    for s in standards:
        if s.get('frequency') in target_freqs:
            std_lookup.setdefault(s['component'], []).append(s)

    # Build inspection item list
    items = []
    seen = set()
    for inv in inventory:
        comp = inv.get('component', '')
        if comp not in std_lookup:
            continue
        for std in std_lookup[comp]:
            key = (inv['id'], std['id'])
            if key in seen: continue
            seen.add(key)
            items.append({
                'inventory_id':  inv['id'],
                'bldg_num':      inv['bldg_num'],
                'floor':         inv.get('floor',''),
                'room':          inv.get('room',''),
                'system_type':   inv.get('system_type',''),
                'component':     comp,
                'address':       inv.get('address',''),
                'reference':     std.get('reference',''),
                'frequency':     std.get('frequency',''),
                'procedure':     std.get('procedure',''),
                'criteria':      std.get('criteria',''),
                'time_min':      std.get('time_min'),
                # form fields (blank initially)
                'status':        '',
                'reading':       '',
                'comments':      '',
            })

    return items

# ── schedule ──────────────────────────────────────────────────────────────────

def get_sprinkler_schedule(month=None, freq_type=None):
    if not _use_supabase(): return []
    try:
        q = _sb().table("sprinkler_schedule").select("*")
        if month and month != 'All': q = q.eq("month", month)
        if freq_type and freq_type != 'All': q = q.eq("freq_type", freq_type)
        return q.order("bldg_num").execute().data or []
    except Exception as e:
        print("get_sprinkler_schedule error:", e); return []

def update_sprinkler_schedule_status(id, status, date_completed=None, notes=None):
    if not _use_supabase(): return
    try:
        upd = {"status": status}
        if date_completed: upd["date_completed"] = date_completed
        if notes is not None: upd["notes"] = notes
        _sb().table("sprinkler_schedule").update(upd).eq("id", id).execute()
    except Exception as e:
        print("update_sprinkler_schedule_status error:", e)

# ── inspections ───────────────────────────────────────────────────────────────

def save_sprinkler_inspection(header, items):
    """
    header: dict with bldg_num, bldg_name, freq_type, inspection_date,
                       inspector_name, overall_result, notes
    items:  list of dicts with component, system_type, floor, room,
                       reference, frequency, procedure, criteria,
                       status, reading, comments
    Returns inspection id or None.
    """
    if not _use_supabase(): return None
    try:
        sb = _sb()
        header = dict(header)
        header['created_at'] = str(date.today())
        res = sb.table("sprinkler_inspections").insert(header).execute()
        insp_id = res.data[0]['id']
        if items:
            rows = [dict(it, inspection_id=insp_id) for it in items]
            # Insert in batches of 200
            for i in range(0, len(rows), 200):
                sb.table("sprinkler_inspection_items").insert(rows[i:i+200]).execute()
        return insp_id
    except Exception as e:
        print("save_sprinkler_inspection error:", e); return None

def get_sprinkler_inspections(bldg_num=None):
    if not _use_supabase(): return []
    try:
        q = (_sb().table("sprinkler_inspections")
             .select("*").order("inspection_date", desc=True))
        if bldg_num:
            q = q.eq("bldg_num", str(bldg_num))
        return q.execute().data or []
    except Exception as e:
        print("get_sprinkler_inspections error:", e); return []

def get_sprinkler_inspection_items(insp_id):
    if not _use_supabase(): return []
    try:
        res = (_sb().table("sprinkler_inspection_items")
               .select("*").eq("inspection_id", insp_id).execute())
        return res.data or []
    except Exception as e:
        print("get_sprinkler_inspection_items error:", e); return []

# ── dashboard stats ───────────────────────────────────────────────────────────

def get_sprinkler_dashboard_stats():
    if not _use_supabase():
        return {"total_systems": 0, "quarterly_due": 0, "annual_due": 0,
                "overdue": 0, "complete": 0, "by_month": [], "by_freq": []}
    try:
        sb = _sb()
        buildings  = get_sprinkler_buildings()
        schedule   = get_sprinkler_schedule()
        inspections = sb.table("sprinkler_inspections").select("id").execute().data or []

        cur_month = date.today().strftime('%B')
        MONTHS = ['January','February','March','April','May','June',
                  'July','August','September','October','November','December']
        cur_idx = MONTHS.index(cur_month)

        total    = len(buildings)
        complete = sum(1 for s in schedule if s.get('status') == 'Complete')
        overdue  = sum(1 for s in schedule
                       if s.get('status') not in ('Complete','Construction')
                       and s.get('month') in MONTHS
                       and MONTHS.index(s['month']) < cur_idx)
        quarterly_due = sum(1 for s in schedule
                            if s.get('freq_type') == 'Quarterly'
                            and s.get('month') == cur_month
                            and s.get('status') != 'Complete')
        annual_due    = sum(1 for s in schedule
                            if s.get('freq_type') == 'Annual'
                            and s.get('month') == cur_month
                            and s.get('status') != 'Complete')

        month_counts = {}
        for r in schedule:
            m = r.get('month','')
            if m not in month_counts:
                month_counts[m] = {'month': m, 'total': 0, 'complete': 0}
            month_counts[m]['total'] += 1
            if r.get('status') == 'Complete': month_counts[m]['complete'] += 1

        freq_counts = {}
        for r in schedule:
            f = r.get('freq_type','')
            if f not in freq_counts:
                freq_counts[f] = {'freq_type': f, 'total': 0, 'complete': 0}
            freq_counts[f]['total'] += 1
            if r.get('status') == 'Complete': freq_counts[f]['complete'] += 1

        return {
            "total_systems":  total,
            "complete":       complete,
            "overdue":        overdue,
            "quarterly_due":  quarterly_due,
            "annual_due":     annual_due,
            "reports_saved":  len(inspections),
            "by_month":       list(month_counts.values()),
            "by_freq":        list(freq_counts.values()),
        }
    except Exception as e:
        print("get_sprinkler_dashboard_stats error:", e)
        return {"total_systems": 0, "quarterly_due": 0, "annual_due": 0,
                "overdue": 0, "complete": 0, "reports_saved": 0,
                "by_month": [], "by_freq": []}
