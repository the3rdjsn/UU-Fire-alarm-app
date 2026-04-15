import logging
import sqlite3, json, os
from datetime import date, datetime

from normalize_utils import clean_seed_payload, normalize_bldg_num

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'fire_alarm.db')

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(buildings, schedule, devices):
    buildings, schedule, devices = clean_seed_payload(buildings, schedule, devices)
    conn = get_conn()
    c = conn.cursor()

    c.executescript('''
        CREATE TABLE IF NOT EXISTS buildings (
            id INTEGER PRIMARY KEY,
            bldg_num TEXT UNIQUE,
            name TEXT, report_name TEXT, district TEXT,
            address TEXT, city TEXT, state TEXT, zip TEXT,
            built INTEGER, sq_ft INTEGER, aux TEXT,
            panel_type TEXT, year_installed INTEGER, age INTEGER,
            gateway TEXT, inspection_month TEXT,
            scheduled_date TEXT, replacement_priority INTEGER,
            replacement_cost REAL, replacement_scheduled TEXT,
            gateway_ip TEXT, anx_ip TEXT, subnet TEXT, vlan TEXT,
            nodes INTEGER, transponders INTEGER,
            smoke INTEGER, heat INTEGER, pull INTEGER, duct INTEGER,
            init_devices INTEGER, notif_devices REAL,
            panel_location TEXT, focalpoint_name TEXT,
            time_to_test INTEGER, aim_asset TEXT
        );
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT, bldg_num TEXT, building_name TEXT,
            district TEXT, address TEXT, est_hours REAL,
            inspection_date TEXT, status TEXT,
            date_completed TEXT, uploaded_cms TEXT, notes TEXT
        );
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building TEXT, type TEXT, point TEXT, description TEXT
        );
        CREATE TABLE IF NOT EXISTS inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bldg_num TEXT, building_name TEXT, district TEXT,
            inspection_date TEXT, work_order TEXT,
            inspection_type TEXT, result TEXT,
            ps_total INTEGER, ps_tested INTEGER,
            sd_total INTEGER, sd_tested INTEGER,
            hd_total INTEGER, hd_tested INTEGER,
            dd_total INTEGER, dd_tested INTEGER,
            wf_total INTEGER, wf_tested INTEGER,
            ts_total INTEGER, ts_tested INTEGER,
            notif_total INTEGER, notif_tested INTEGER,
            trans_total INTEGER, trans_tested INTEGER,
            aes_alarm TEXT, aes_supv TEXT, aes_trouble TEXT,
            aes_wf TEXT, aes_tamper TEXT, aes_duct TEXT, aes_ext TEXT,
            deficiencies TEXT,
            notes TEXT, inspector_name TEXT,
            pct_tested REAL, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS deficiencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inspection_id INTEGER, device_type TEXT,
            location TEXT, issue TEXT, part_number TEXT,
            corrected_onsite TEXT,
            FOREIGN KEY(inspection_id) REFERENCES inspections(id)
        );
    ''')

    # Seed buildings if empty
    if c.execute('SELECT COUNT(*) FROM buildings').fetchone()[0] == 0:
        for b in buildings:
            try:
                c.execute('''INSERT OR IGNORE INTO buildings VALUES
                    (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (b['bldg_num'],
                     b['name'], b['report_name'],
                     b['district'], b['address'],
                     b['city'], b['state'], b['zip'],
                     b['built'], b['sq_ft'],
                     b['aux'], b['panel_type'],
                     b['year_installed'], b['age'],
                     b['gateway'], b['inspection_month'],
                     b['scheduled_date'],
                     b['replacement_priority'],
                     b['replacement_cost'],
                     b['replacement_scheduled'],
                     b['gateway_ip'], b['anx_ip'],
                     b['subnet'], b['vlan'],
                     b['nodes'], b['transponders'],
                     b['smoke'], b['heat'],
                     b['pull'], b['duct'],
                     b['init_devices'],
                     b['notif_devices'],
                     b['panel_location'], b['focalpoint_name'],
                     b['time_to_test'], b['aim_asset']))
            except Exception:
                logger.exception('Failed to seed building %s', b.get('bldg_num'))

    # Seed schedule if empty
    if c.execute('SELECT COUNT(*) FROM schedule').fetchone()[0] == 0:
        for s in schedule:
            try:
                c.execute('''INSERT INTO schedule 
                    (month, bldg_num, building_name, district, address,
                     est_hours, inspection_date, status, date_completed,
                     uploaded_cms, notes)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                    (s['month'], s['bldg_num'], s['building_name'], s['district'],
                     s['address'], s['est_hours'], s['inspection_date'], s['status'],
                     s['date_completed'], s['uploaded_cms'], s['notes']))
            except Exception:
                logger.exception('Failed to seed schedule row for building %s', s.get('bldg_num'))

    # Seed devices if empty
    if c.execute('SELECT COUNT(*) FROM devices').fetchone()[0] == 0:
        try:
            c.executemany('INSERT INTO devices (building,type,point,description) VALUES (?,?,?,?)',
                          [(d['building'], d['type'], d['point'], d['description']) for d in devices])
        except Exception:
            logger.exception('Failed to seed devices')

    conn.commit()
    conn.close()

def get_buildings():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM buildings ORDER BY name').fetchall()]

def get_building(bldg_num):
    with get_conn() as conn:
        r = conn.execute('SELECT * FROM buildings WHERE bldg_num=?', (normalize_bldg_num(bldg_num),)).fetchone()
        return dict(r) if r else None

def get_schedule(month=None):
    with get_conn() as conn:
        if month and month != 'All':
            rows = conn.execute('SELECT * FROM schedule WHERE month=? ORDER BY inspection_date', (month,)).fetchall()
        else:
            rows = conn.execute('''SELECT * FROM schedule ORDER BY 
                CASE month 
                WHEN "January" THEN 1 WHEN "February" THEN 2 WHEN "March" THEN 3
                WHEN "April" THEN 4 WHEN "May" THEN 5 WHEN "June" THEN 6
                WHEN "July" THEN 7 WHEN "August" THEN 8 WHEN "September" THEN 9
                WHEN "October" THEN 10 WHEN "November" THEN 11 WHEN "December" THEN 12
                END, inspection_date''').fetchall()
        return [dict(r) for r in rows]

def update_schedule_status(sched_id, status, date_completed=None, notes=None, uploaded_cms=None):
    with get_conn() as conn:
        conn.execute('''UPDATE schedule SET status=?, date_completed=?,
                        notes=COALESCE(?,notes), uploaded_cms=COALESCE(?,uploaded_cms)
                        WHERE id=?''',
                     (status, date_completed, notes, uploaded_cms, sched_id))
        conn.commit()

def get_devices_for_building(fp_name, bldg_name):
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM devices WHERE building=? OR building=? ORDER BY type, point',
            (fp_name, bldg_name)).fetchall()
        return [dict(r) for r in rows]

def save_inspection(data, deficiencies):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO inspections
            (bldg_num, building_name, district, inspection_date, work_order,
             inspection_type, result,
             ps_total, ps_tested, sd_total, sd_tested,
             hd_total, hd_tested, dd_total, dd_tested,
             wf_total, wf_tested, ts_total, ts_tested,
             notif_total, notif_tested, trans_total, trans_tested,
             aes_alarm, aes_supv, aes_trouble, aes_wf, aes_tamper, aes_duct, aes_ext,
             deficiencies, notes, inspector_name, pct_tested, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (normalize_bldg_num(data['bldg_num']), data['building_name'], data['district'],
             data['inspection_date'], data['work_order'], data['inspection_type'],
             data['result'],
             data.get('ps_total'), data.get('ps_tested'),
             data.get('sd_total'), data.get('sd_tested'),
             data.get('hd_total'), data.get('hd_tested'),
             data.get('dd_total'), data.get('dd_tested'),
             data.get('wf_total'), data.get('wf_tested'),
             data.get('ts_total'), data.get('ts_tested'),
             data.get('notif_total'), data.get('notif_tested'),
             data.get('trans_total'), data.get('trans_tested'),
             data.get('aes_alarm','PASS'), data.get('aes_supv','PASS'),
             data.get('aes_trouble','PASS'), data.get('aes_wf','PASS'),
             data.get('aes_tamper','PASS'), data.get('aes_duct','PASS'),
             data.get('aes_ext','PASS'),
             json.dumps(deficiencies), data.get('notes',''),
             data.get('inspector_name',''), data.get('pct_tested',0),
             datetime.now().isoformat()))
        insp_id = c.lastrowid
        # Update schedule status
        conn.execute('''UPDATE schedule SET status="Complete", date_completed=?
                        WHERE bldg_num=?''',
                     (data['inspection_date'], normalize_bldg_num(data['bldg_num'])))
        conn.commit()
        return insp_id

def get_inspections(bldg_num=None):
    with get_conn() as conn:
        if bldg_num:
            rows = conn.execute('SELECT * FROM inspections WHERE bldg_num=? ORDER BY inspection_date DESC', (normalize_bldg_num(bldg_num),)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM inspections ORDER BY created_at DESC').fetchall()
        return [dict(r) for r in rows]


def delete_inspection(insp_id):
    with get_conn() as conn:
        conn.execute('DELETE FROM inspections WHERE id=?', (insp_id,))
        conn.commit()

def get_dashboard_stats():
    with get_conn() as conn:
        total   = conn.execute('SELECT COUNT(*) FROM buildings').fetchone()[0]
        sched   = conn.execute('SELECT COUNT(*) FROM schedule').fetchone()[0]
        done    = conn.execute('SELECT COUNT(*) FROM schedule WHERE status="Complete"').fetchone()[0]
        # Overdue = month has passed this cycle and not complete
        import datetime as _dt
        _months = ['January','February','March','April','May','June',
                   'July','August','September','October','November','December']
        _cur = _dt.date.today().month
        _past = [m for m in _months if _months.index(m)+1 < _cur]
        _placeholders = ','.join('?' for _ in _past) if _past else "''"
        overdue = conn.execute(
            f'SELECT COUNT(*) FROM schedule WHERE status!="Complete" AND status!="Construction" AND month IN ({_placeholders})',
            _past).fetchone()[0] if _past else 0
        saved   = conn.execute('SELECT COUNT(*) FROM inspections').fetchone()[0]
        init_dev= conn.execute('SELECT SUM(init_devices) FROM buildings').fetchone()[0] or 0
        by_month= conn.execute('''SELECT month, 
                    SUM(CASE WHEN status="Complete" THEN 1 ELSE 0 END) as done,
                    COUNT(*) as total
                    FROM schedule GROUP BY month''').fetchall()
        by_dist = conn.execute('''SELECT district, COUNT(*) as cnt FROM buildings
                    WHERE district IS NOT NULL AND district != ""
                    GROUP BY district ORDER BY cnt DESC''').fetchall()
        return {
            'total_buildings': total, 'scheduled': sched,
            'complete': done, 'overdue': overdue, 'saved_reports': saved,
            'init_devices': int(init_dev),
            'by_month': [dict(r) for r in by_month],
            'by_district': [dict(r) for r in by_dist],
        }

def refresh_overdue_statuses():
    """Recalculate overdue status for all non-complete schedule entries on every app load."""
    MONTHS_LIST = ['January','February','March','April','May','June',
                   'July','August','September','October','November','December']
    cur_month = date.today().month
    past_months = [m for m in MONTHS_LIST if MONTHS_LIST.index(m) + 1 < cur_month]
    with get_conn() as conn:
        if past_months:
            placeholders = ','.join('?' for _ in past_months)
            conn.execute(
                f"UPDATE schedule SET status='Overdue' WHERE status NOT IN ('Complete','Construction') AND month IN ({placeholders})",
                past_months)
        # Anything in current or future month that is not Complete → Pending (not Overdue)
        future_months = [m for m in MONTHS_LIST if MONTHS_LIST.index(m) + 1 >= cur_month]
        if future_months:
            placeholders2 = ','.join('?' for _ in future_months)
            conn.execute(
                f"UPDATE schedule SET status='Pending' WHERE status='Overdue' AND month IN ({placeholders2})",
                future_months)
        conn.commit()

def get_inspection(insp_id):
    with get_conn() as conn:
        r = conn.execute('SELECT * FROM inspections WHERE id=?', (insp_id,)).fetchone()
        return dict(r) if r else None

def update_inspection(insp_id, data, deficiencies):
    total = sum([data.get(f'{c}_total') or 0 for c in ['ps','sd','hd','dd','wf','ts','notif','trans']])
    tested = sum([data.get(f'{c}_tested') or 0 for c in ['ps','sd','hd','dd','wf','ts','notif','trans']])
    pct = round(tested / total * 100) if total > 0 else 0
    with get_conn() as conn:
        conn.execute('''UPDATE inspections SET
            inspection_date=?, work_order=?, inspection_type=?, result=?,
            ps_total=?, ps_tested=?, sd_total=?, sd_tested=?,
            hd_total=?, hd_tested=?, dd_total=?, dd_tested=?,
            wf_total=?, wf_tested=?, ts_total=?, ts_tested=?,
            notif_total=?, notif_tested=?, trans_total=?, trans_tested=?,
            aes_alarm=?, aes_supv=?, aes_trouble=?, aes_wf=?, aes_tamper=?, aes_duct=?, aes_ext=?,
            deficiencies=?, notes=?, inspector_name=?, pct_tested=?
            WHERE id=?''',
            (data['inspection_date'], data['work_order'], data['inspection_type'], data['result'],
             data.get('ps_total'), data.get('ps_tested'),
             data.get('sd_total'), data.get('sd_tested'),
             data.get('hd_total'), data.get('hd_tested'),
             data.get('dd_total'), data.get('dd_tested'),
             data.get('wf_total'), data.get('wf_tested'),
             data.get('ts_total'), data.get('ts_tested'),
             data.get('notif_total'), data.get('notif_tested'),
             data.get('trans_total'), data.get('trans_tested'),
             data.get('aes_alarm','PASS'), data.get('aes_supv','PASS'),
             data.get('aes_trouble','PASS'), data.get('aes_wf','PASS'),
             data.get('aes_tamper','PASS'), data.get('aes_duct','PASS'),
             data.get('aes_ext','PASS'),
             json.dumps(deficiencies), data.get('notes',''),
             data.get('inspector_name',''), pct, insp_id))
        conn.commit()

def save_device_results(insp_id, device_results):
    """Save per-device pass/fail/na results as JSON blob on the inspection."""
    with get_conn() as conn:
        # Add column if it doesn't exist yet (migration for existing DBs)
        try:
            conn.execute('ALTER TABLE inspections ADD COLUMN device_results TEXT')
            conn.commit()
        except: pass
        conn.execute('UPDATE inspections SET device_results=? WHERE id=?',
                     (json.dumps(device_results), insp_id))
        conn.commit()

def get_device_results(insp_id):
    with get_conn() as conn:
        # Add column if it doesn't exist yet
        try:
            conn.execute('ALTER TABLE inspections ADD COLUMN device_results TEXT')
            conn.commit()
        except: pass
        r = conn.execute('SELECT device_results FROM inspections WHERE id=?', (insp_id,)).fetchone()
        if r and r[0]:
            return json.loads(r[0])
        return {}

def update_building(bldg_num, fields):
    """Update editable building fields."""
    allowed = ['name','district','address','city','state','zip','built','sq_ft',
               'aux','panel_type','year_installed','age','gateway','inspection_month',
               'replacement_priority','gateway_ip','anx_ip','subnet','vlan',
               'nodes','transponders','smoke','heat','pull','duct',
               'init_devices','notif_devices','panel_location','focalpoint_name',
               'time_to_test','aim_asset']
    sets = ', '.join(f'{k}=?' for k in fields if k in allowed)
    vals = [v for k,v in fields.items() if k in allowed]
    if not sets: return
    with get_conn() as conn:
        conn.execute(f'UPDATE buildings SET {sets} WHERE bldg_num=?', vals + [normalize_bldg_num(bldg_num)])
        conn.commit()

def save_building_image(bldg_num, image_bytes, ext='jpg'):
    """Save building image to images/ folder."""
    import os
    img_dir = os.path.join(os.path.dirname(__file__), 'images')
    os.makedirs(img_dir, exist_ok=True)
    path = os.path.join(img_dir, f'{bldg_num}.{ext}')
    with open(path, 'wb') as f:
        f.write(image_bytes)
    return path

def get_building_image(bldg_num):
    """Return base64 encoded building image if it exists."""
    import os, base64
    img_dir = os.path.join(os.path.dirname(__file__), 'images')
    for ext in ['jpg','jpeg','png','JPG','JPEG','PNG']:
        path = os.path.join(img_dir, f'{bldg_num}.{ext}')
        if os.path.exists(path):
            with open(path, 'rb') as f:
                return base64.b64encode(f.read()).decode(), ext
    return None, None

def get_device_buildings():
    with get_conn() as conn:
        rows = conn.execute('SELECT DISTINCT building FROM devices ORDER BY building').fetchall()
    return [r[0] for r in rows]

def search_devices(search, type_f, bldg_f):
    import pandas as pd
    with get_conn() as conn:
        q = 'SELECT building, type, point, description FROM devices WHERE 1=1'
        params = []
        if type_f and type_f != 'All':
            q += ' AND type=?'; params.append(type_f)
        if bldg_f and bldg_f != 'All':
            q += ' AND building=?'; params.append(bldg_f)
        if search:
            q += ' AND (building LIKE ? OR type LIKE ? OR point LIKE ? OR description LIKE ?)'
            s = f'%{search}%'; params.extend([s, s, s, s])
        q += ' ORDER BY building, type, point LIMIT 2000'
        rows = conn.execute(q, params).fetchall()
    return pd.DataFrame(rows, columns=['Building','Type','Point','Description'])
