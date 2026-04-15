"""
db_supabase.py — Supabase (PostgreSQL) backend.
Drop-in replacement for db.py when SUPABASE_URL + SUPABASE_KEY are set.
Falls back to SQLite automatically if env vars are missing (local dev).
"""
import os, json
import streamlit as st
from datetime import date

# ── Connection ────────────────────────────────────────────────────────────────
def _use_supabase():
    return bool(os.environ.get('SUPABASE_URL') and os.environ.get('SUPABASE_KEY'))

@st.cache_resource
def _get_supabase():
    from supabase import create_client
    url = os.environ['SUPABASE_URL']
    key = os.environ['SUPABASE_KEY']
    return create_client(url, key)

def _sb():
    return _get_supabase()

# ── Init / Seed ───────────────────────────────────────────────────────────────
MONTHS_LIST = ['January','February','March','April','May','June',
               'July','August','September','October','November','December']

def init_db(buildings, schedule, devices):
    if _use_supabase():
        _seed_supabase(buildings, schedule, devices)
    else:
        import db as _sqlite_db
        _sqlite_db.init_db(buildings, schedule, devices)

def _seed_supabase(buildings, schedule, devices):
    sb = _sb()

    # ── Buildings ──────────────────────────────────────────────────────────────
    existing = sb.table('buildings').select('bldg_num').execute()
    if not existing.data:
        def _safe_int(v):
            try: n = int(float(str(v))); return n if n else None
            except: return None
        def _safe_float(v):
            try: n = float(str(v)); return n if n else None
            except: return None
        rows = []
        for b in buildings:
            # Support both raw JSON keys and pre-mapped keys
            bldg_num = str(b.get('Bldg #') or b.get('bldg_num') or '').split('.')[0].strip()
            if not bldg_num or bldg_num == 'None': continue
            rows.append({
                'bldg_num':             bldg_num,
                'name':                 b.get('Building Name') or b.get('building_name') or b.get('name',''),
                'report_name':          b.get('Report Name') or b.get('report_name',''),
                'district':             b.get('District') or b.get('district',''),
                'address':              b.get('Street Address') or b.get('address',''),
                'city':                 b.get('City') or b.get('city',''),
                'state':                b.get('State') or b.get('state',''),
                'zip':                  str(b.get('Zip') or b.get('zip','') or ''),
                'built':                _safe_int(b.get('Built') or b.get('built')),
                'sq_ft':                _safe_int(b.get('Gross Sq Ft') or b.get('sq_ft')),
                'aux':                  b.get('Aux (Yes/No)') or b.get('aux',''),
                'panel_type':           b.get('Panel Type') or b.get('panel_type',''),
                'year_installed':       _safe_int(b.get('Year Installed') or b.get('year_installed')),
                'age':                  _safe_int(b.get('Age Of System') or b.get('age')),
                'gateway':              b.get('Gateway  (Yes/No)') or b.get('gateway',''),
                'inspection_month':     b.get('Inspection Month') or b.get('inspection_month',''),
                'replacement_priority': _safe_int(b.get('Critical Replacement (1-5, 5 Being Most Critical)') or b.get('replacement_priority')),
                'gateway_ip':           b.get('Gateway Ip Addresses') or b.get('gateway_ip',''),
                'anx_ip':               b.get('Anx Ip Addresses') or b.get('anx_ip',''),
                'subnet':               b.get('Subnet') or b.get('subnet',''),
                'vlan':                 str(b.get('Vlan') or b.get('vlan','') or ''),
                'nodes':                _safe_int(b.get('Nodes') or b.get('nodes')),
                'transponders':         _safe_int(b.get('Transponders') or b.get('transponders')),
                'smoke':                _safe_int(b.get('Smoke Detectors') or b.get('smoke')),
                'heat':                 _safe_int(b.get('Heat Detectors') or b.get('heat')),
                'pull':                 _safe_int(b.get('Pull Stations') or b.get('pull')),
                'duct':                 _safe_int(b.get('Duct Dectors') or b.get('duct')),
                'init_devices':         _safe_int(b.get('Intitiation Devices') or b.get('init_devices')),
                'notif_devices':        _safe_float(b.get('Notification Devices') or b.get('notif_devices')),
                'panel_location':       b.get('Panel Location') or b.get('panel_location',''),
                'focalpoint_name':      b.get('FocalPoint Name') or b.get('focalpoint_name',''),
                'time_to_test':         _safe_int(b.get('Time To Test') or b.get('time_to_test')),
                'aim_asset':            b.get('aim_asset',''),
            })
        for i in range(0, len(rows), 100):
            sb.table('buildings').insert(rows[i:i+100]).execute()

    # ── Schedule ───────────────────────────────────────────────────────────────
    existing = sb.table('schedule').select('id').limit(1).execute()
    if not existing.data:
        cur_month = date.today().month
        rows = []
        for s in schedule:
            completed = str(s.get('completed',''))
            insp_date = s.get('inspection_date','')
            if insp_date in ('None','nan',''): insp_date = None
            if insp_date and len(str(insp_date)) > 10: insp_date = str(insp_date)[:10]
            s_month = s.get('month','')
            month_num = MONTHS_LIST.index(s_month)+1 if s_month in MONTHS_LIST else 99
            if insp_date == 'CONSTRUCTION':
                status = 'Construction'; insp_date = None
            elif completed in ('3','3.0'):
                status = 'Complete'
            elif month_num < cur_month:
                status = 'Overdue'
            else:
                status = 'Pending'
            rows.append({
                'month':         s_month,
                'bldg_num':      normalize_bldg_num(s.get('bldg_num')),
                'building_name': s.get('building_name',''),
                'district':      s.get('district',''),
                'address':       s.get('address',''),
                'est_hours':     s.get('est_hours'),
                'inspection_date': insp_date,
                'status':        status,
                'date_completed': None,
                'uploaded_cms':  s.get('uploaded_cms','No') or 'No',
                'notes':         '',
            })
        for i in range(0, len(rows), 100):
            sb.table('schedule').insert(rows[i:i+100]).execute()

    # ── Devices ────────────────────────────────────────────────────────────────
    existing = sb.table('devices').select('id').limit(1).execute()
    if not existing.data:
        rows = [{
            'building': d['building'],
            'type': d['type'],
            'point': d['point'],
            'description': d['description'],
        } for d in devices]
        for i in range(0, len(rows), 500):
            sb.table('devices').insert(rows[i:i+500]).execute()

# ── Overdue refresh ───────────────────────────────────────────────────────────
def refresh_overdue_statuses():
    if not _use_supabase():
        import db as _s; _s.refresh_overdue_statuses(); return
    sb = _sb()
    cur_month = date.today().month
    past = [m for m in MONTHS_LIST if MONTHS_LIST.index(m)+1 < cur_month]
    future = [m for m in MONTHS_LIST if MONTHS_LIST.index(m)+1 >= cur_month]
    if past:
        # Mark past months as Overdue if not complete
        all_sched = sb.table('schedule').select('id,month,status').execute().data
        overdue_ids = [r['id'] for r in all_sched
                       if r['month'] in past and r['status'] not in ('Complete','Construction')]
        if overdue_ids:
            sb.table('schedule').update({'status':'Overdue'}).in_('id', overdue_ids).execute()
        # Un-overdue future months
        future_ids = [r['id'] for r in all_sched
                      if r['month'] in future and r['status'] == 'Overdue']
        if future_ids:
            sb.table('schedule').update({'status':'Pending'}).in_('id', future_ids).execute()

# ── Buildings ─────────────────────────────────────────────────────────────────
def get_buildings():
    if not _use_supabase():
        import db as _s; return _s.get_buildings()
    data = _sb().table('buildings').select('*').order('bldg_num').execute().data
    return data

def get_building(bldg_num):
    if not _use_supabase():
        import db as _s; return _s.get_building(bldg_num)
    r = _sb().table('buildings').select('*').eq('bldg_num', str(bldg_num)).execute().data
    return r[0] if r else None

def update_building(bldg_num, fields):
    if not _use_supabase():
        import db as _s; return _s.update_building(bldg_num, fields)
    allowed = ['name','district','address','city','state','zip','built','sq_ft',
               'aux','panel_type','year_installed','age','gateway','inspection_month',
               'replacement_priority','gateway_ip','anx_ip','subnet','vlan',
               'nodes','transponders','smoke','heat','pull','duct',
               'init_devices','notif_devices','panel_location','focalpoint_name',
               'time_to_test','aim_asset']
    clean = {k: v for k, v in fields.items() if k in allowed}
    if clean:
        _sb().table('buildings').update(clean).eq('bldg_num', str(bldg_num)).execute()

def save_building_image(bldg_num, image_bytes, ext='jpg'):
    if not _use_supabase():
        import db as _s; return _s.save_building_image(bldg_num, image_bytes, ext)
    import base64
    b64 = base64.b64encode(image_bytes).decode()
    sb = _sb()
    existing = sb.table('building_images').select('bldg_num').eq('bldg_num', str(bldg_num)).execute()
    if existing.data:
        sb.table('building_images').update({'image_data':b64,'image_ext':ext}).eq('bldg_num', str(bldg_num)).execute()
    else:
        sb.table('building_images').insert({'bldg_num':str(bldg_num),'image_data':b64,'image_ext':ext}).execute()

def get_building_image(bldg_num):
    if not _use_supabase():
        import db as _s; return _s.get_building_image(bldg_num)
    r = _sb().table('building_images').select('image_data,image_ext').eq('bldg_num', str(bldg_num)).execute().data
    if r:
        return r[0]['image_data'], r[0]['image_ext']
    return None, None

# ── Schedule ──────────────────────────────────────────────────────────────────
def get_schedule(month='All'):
    if not _use_supabase():
        import db as _s; return _s.get_schedule(month)
    q = _sb().table('schedule').select('*').order('inspection_date')
    if month and month != 'All':
        q = q.eq('month', month)
    return q.execute().data

def update_schedule_status(id, status, date_completed=None, notes=None, uploaded_cms=None):
    if not _use_supabase():
        import db as _s; return _s.update_schedule_status(id, status, date_completed, notes, uploaded_cms)
    upd = {'status': status}
    if date_completed is not None: upd['date_completed'] = date_completed
    if notes is not None:          upd['notes'] = notes
    if uploaded_cms is not None:   upd['uploaded_cms'] = uploaded_cms
    _sb().table('schedule').update(upd).eq('id', id).execute()

# ── Inspections ───────────────────────────────────────────────────────────────
def save_inspection(data, deficiencies):
    if not _use_supabase():
        import db as _s; return _s.save_inspection(data, deficiencies)
    total  = sum([data.get(f'{c}_total') or 0 for c in ['ps','sd','hd','dd','wf','ts','notif','trans']])
    tested = sum([data.get(f'{c}_tested') or 0 for c in ['ps','sd','hd','dd','wf','ts','notif','trans']])
    pct = round(tested/total*100) if total > 0 else 0
    row = {
        'bldg_num': data['bldg_num'], 'building_name': data['building_name'],
        'district': data.get('district',''), 'inspection_date': data['inspection_date'],
        'work_order': data.get('work_order',''), 'inspection_type': data.get('inspection_type',''),
        'result': data.get('result',''), 'notes': data.get('notes',''),
        'inspector_name': data.get('inspector_name',''), 'pct_tested': pct,
        'ps_total':    data.get('ps_total'),    'ps_tested':    data.get('ps_tested'),
        'sd_total':    data.get('sd_total'),    'sd_tested':    data.get('sd_tested'),
        'hd_total':    data.get('hd_total'),    'hd_tested':    data.get('hd_tested'),
        'dd_total':    data.get('dd_total'),    'dd_tested':    data.get('dd_tested'),
        'wf_total':    data.get('wf_total'),    'wf_tested':    data.get('wf_tested'),
        'ts_total':    data.get('ts_total'),    'ts_tested':    data.get('ts_tested'),
        'notif_total': data.get('notif_total'), 'notif_tested': data.get('notif_tested'),
        'trans_total': data.get('trans_total'), 'trans_tested': data.get('trans_tested'),
        'aes_alarm':   data.get('aes_alarm','PASS'), 'aes_supv':  data.get('aes_supv','PASS'),
        'aes_trouble': data.get('aes_trouble','PASS'),'aes_wf':   data.get('aes_wf','PASS'),
        'aes_tamper':  data.get('aes_tamper','PASS'), 'aes_duct': data.get('aes_duct','PASS'),
        'aes_ext':     data.get('aes_ext','PASS'),
        'deficiencies': json.dumps(deficiencies),
        'created_at':  str(date.today()),
    }
    result = _sb().table('inspections').insert(row).execute()
    return result.data[0]['id']

def save_device_results(insp_id, device_results):
    if not _use_supabase():
        import db as _s; return _s.save_device_results(insp_id, device_results)
    _sb().table('inspections').update({'device_results': json.dumps(device_results)}).eq('id', insp_id).execute()

def get_device_results(insp_id):
    if not _use_supabase():
        import db as _s; return _s.get_device_results(insp_id)
    r = _sb().table('inspections').select('device_results').eq('id', insp_id).execute().data
    if r and r[0].get('device_results'):
        return json.loads(r[0]['device_results'])
    return {}

def get_inspections(bldg_num=None):
    if not _use_supabase():
        import db as _s; return _s.get_inspections(bldg_num)
    q = _sb().table('inspections').select('*').order('inspection_date', desc=True)
    if bldg_num:
        q = q.eq('bldg_num', normalize_bldg_num(bldg_num))
    data = q.execute().data
    # Parse deficiencies back to list
    for row in data:
        if isinstance(row.get('deficiencies'), str):
            try: row['deficiencies'] = json.loads(row['deficiencies'])
            except: row['deficiencies'] = []
    return data

def delete_inspection(insp_id):
    if not _use_supabase():
        import db as _s; return _s.delete_inspection(insp_id)

    _sb().table('deficiencies').delete().eq('inspection_id', insp_id).execute()
    _sb().table('inspections').delete().eq('id', insp_id).execute()

def update_inspection(insp_id, data, deficiencies):
    if not _use_supabase():
        import db as _s; return _s.update_inspection(insp_id, data, deficiencies)
    total  = sum([data.get(f'{c}_total') or 0 for c in ['ps','sd','hd','dd','wf','ts','notif','trans']])
    tested = sum([data.get(f'{c}_tested') or 0 for c in ['ps','sd','hd','dd','wf','ts','notif','trans']])
    pct = round(tested/total*100) if total > 0 else 0
    upd = {**data, 'deficiencies': json.dumps(deficiencies), 'pct_tested': pct}
    _sb().table('inspections').update(upd).eq('id', insp_id).execute()

# ── Devices ───────────────────────────────────────────────────────────────────
def get_devices_for_building(fp_name, bldg_name):
    if not _use_supabase():
        import db as _s; return _s.get_devices_for_building(fp_name, bldg_name)
    sb = _sb()
    if fp_name:
        r = sb.table('devices').select('*').eq('building', fp_name).order('type').execute().data
        if r: return r
    if bldg_name:
        r = sb.table('devices').select('*').ilike('building', f'%{bldg_name[:8]}%').order('type').execute().data
        if r: return r
    return []

# ── Dashboard stats ───────────────────────────────────────────────────────────
def get_dashboard_stats():
    if not _use_supabase():
        import db as _s; return _s.get_dashboard_stats()
    sb = _sb()
    buildings_data  = sb.table('buildings').select('id,init_devices,district').execute().data
    total_buildings = len(buildings_data)
    total_devices   = sum(int(b.get('init_devices') or 0) for b in buildings_data)
    sched_data      = sb.table('schedule').select('status,month,district').execute().data
    scheduled       = len(sched_data)
    complete        = sum(1 for r in sched_data if r['status'] == 'Complete')
    overdue         = sum(1 for r in sched_data if r['status'] == 'Overdue')
    saved_reports   = len(sb.table('inspections').select('id').execute().data)
    done_pct        = round(complete/scheduled*100) if scheduled else 0
    month_counts = {}
    for r in sched_data:
        m = r.get('month','')
        if m not in month_counts:
            month_counts[m] = {'month': m, 'total': 0, 'complete': 0, 'overdue': 0}
        month_counts[m]['total'] += 1
        if r['status'] == 'Complete':  month_counts[m]['complete'] += 1
        if r['status'] == 'Overdue':   month_counts[m]['overdue'] += 1
    by_month = list(month_counts.values())
    dist_counts = {}
    for r in sched_data:
        d = r.get('district','')
        if d not in dist_counts:
            dist_counts[d] = {'district': d, 'cnt': 0, 'complete': 0}
        dist_counts[d]['cnt'] += 1
        if r['status'] == 'Complete': dist_counts[d]['complete'] += 1
    by_district = list(dist_counts.values())
    return {
        'total_buildings': total_buildings,
        'scheduled': scheduled,
        'complete': complete,
        'overdue': overdue,
        'saved_reports': saved_reports,
        'done_pct': done_pct,
        'init_devices': total_devices,
        'by_month': by_month,
        'by_district': by_district,
    }


def get_device_buildings():
    """Return sorted list of distinct building names from devices table."""
    if not _use_supabase():
        import db as _s; return _s.get_device_buildings()
    import sqlite3
    # Use local SQLite if available, else Supabase
    data = _sb().table('devices').select('building').execute().data
    names = sorted(set(r['building'] for r in data if r.get('building')))
    return names

def search_devices(search, type_f, bldg_f):
    """Search devices with filters, return DataFrame."""
    import pandas as pd
    if not _use_supabase():
        import db as _s; return _s.search_devices(search, type_f, bldg_f)
    sb = _sb()
    q = sb.table('devices').select('building,type,point,description')
    if type_f and type_f != 'All':
        q = q.eq('type', type_f)
    if bldg_f and bldg_f != 'All':
        q = q.eq('building', bldg_f)
    if search:
        # Supabase full-text: use ilike on building as primary filter
        q = q.ilike('building', f'%{search}%')
    q = q.order('building').order('type').order('point').limit(2000)
    data = q.execute().data
    # If search didn't match building, try other fields
    if search and not data:
        data = sb.table('devices').select('building,type,point,description')            .ilike('description', f'%{search}%').order('building').limit(2000).execute().data
    return pd.DataFrame(data, columns=['building','type','point','description'])             .rename(columns={'building':'Building','type':'Type','point':'Point','description':'Description'})
