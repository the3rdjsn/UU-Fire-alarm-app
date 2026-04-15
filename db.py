import sqlite3, json, os, logging
from datetime import date, datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'fire_alarm.db')

MONTHS_LIST = ['January','February','March','April','May','June',
               'July','August','September','October','November','December']

def canonicalize_district(value):
    if value is None:
        return ''
    text = str(value).strip()
    if not text or text.lower() in ('nan', 'none'):
        return ''
    cleaned = ' '.join(text.replace('_', ' ').split()).upper()
    aliases = {
        'ENGINERING': 'ENGINEERING',
        'ENGINEERING': 'ENGINEERING',
        'HEALTH SCIENCE': 'HEALTH SCIENCE',
        'ACADEMIC': 'ACADEMIC',
        'VENUES': 'VENUES',
        'PRESIDENTS': 'PRESIDENTS',
        'SCIENCE': 'SCIENCE',
        'CORE': 'CORE',
        'HRE': 'HRE',
        'USA': 'USA',
        'GUEST': 'GUEST',
        'PARKING': 'PARKING',
    }
    return aliases.get(cleaned, cleaned)

def parse_schedule_date(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ('nan', 'none'):
        return None
    if text.upper().startswith('NEW CONSTR'):
        return None
    try:
        return datetime.fromisoformat(text[:10]).date()
    except Exception:
        return None

def is_schedule_overdue(row, today=None):
    today = today or date.today()
    status = str(row.get('status') or '').strip()
    if status in ('Complete', 'Construction'):
        return False

    sched_date = parse_schedule_date(row.get('inspection_date'))
    if sched_date is not None:
        return sched_date < today

    month = str(row.get('month') or '').strip()
    if month in MONTHS_LIST:
        return MONTHS_LIST.index(month) + 1 < today.month
    return False

logger = logging.getLogger(__name__)

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(buildings, schedule, devices):
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
                    (str(b.get('Bldg #','')).split('.')[0],
                     b.get('Building Name',''), b.get('Report Name',''),
                     b.get('District',''), b.get('Street Address',''),
                     b.get('City',''), b.get('State',''), str(b.get('Zip','')),
                     b.get('Built'), b.get('Gross Sq Ft'),
                     b.get('Aux (Yes/No)',''), b.get('Panel Type',''),
                     b.get('Year Installed'), b.get('Age Of System'),
                     b.get('Gateway  (Yes/No)',''), b.get('Inspection Month',''),
                     b.get('Inspection Date'), 
                     b.get('Critical Replacement (1-5, 5 Being Most Critical)'),
                     b.get('Replacement Cost'),
                     b.get('Replacement Scheduled (Yes/No/Na)',''),
                     b.get('Gateway Ip Addresses',''), b.get('Anx Ip Addresses',''),
                     b.get('Subnet',''), str(b.get('Vlan','')),
                     b.get('Nodes'), b.get('Transponders'),
                     b.get('Smoke Detectors'), b.get('Heat Detectors'),
                     b.get('Pull Stations'), b.get('Duct Dectors'),
                     b.get('Intitiation Devices'),
                     b.get('Notification Devices'),
                     b.get('Panel Location',''), b.get('FocalPoint Name',''),
                     b.get('Time To Test'), b.get('Aim Asset Number','')))
            except Exception as e:
                logger.exception("Failed to seed building row: %s", b)

    # Seed schedule if empty
    if c.execute('SELECT COUNT(*) FROM schedule').fetchone()[0] == 0:
        for s in schedule:
            completed = str(s.get('completed',''))
            insp_date = s.get('inspection_date','')
            if insp_date in ('None','nan',''): insp_date = None
            if insp_date and len(str(insp_date)) > 10: insp_date = str(insp_date)[:10]
            
            MONTHS_LIST = ['January','February','March','April','May','June',
                           'July','August','September','October','November','December']
            s_month = s.get('month','')
            month_num = MONTHS_LIST.index(s_month) + 1 if s_month in MONTHS_LIST else 99
            cur_month = date.today().month

            if completed in ('3','3.0'):
                status = 'Complete'
            elif insp_date == 'CONSTRUCTION':
                status = 'Construction'
                insp_date = None
            elif month_num < cur_month:
                # Inspection month fully passed this cycle without completion
                status = 'Overdue'
            else:
                status = 'Pending'

            c.execute('''INSERT INTO schedule 
                (month, bldg_num, building_name, district, address,
                 est_hours, inspection_date, status, date_completed,
                 uploaded_cms, notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                (s.get('month',''),
                 normalize_bldg_num(s.get('bldg_num')),
                 s.get('building_name',''), s.get('district',''),
                 s.get('address',''), s.get('est_hours'),
                 insp_date, status, None,
                 'Yes' if s.get('uploaded_cms')==1 else 'No', ''))

    # Seed devices if empty
    if c.execute('SELECT COUNT(*) FROM devices').fetchone()[0] == 0:
        c.executemany('INSERT INTO devices (building,type,point,description) VALUES (?,?,?,?)',
                      [(d['building'], d['type'], d['point'], d['description']) for d in devices])

    conn.commit()
    conn.close()

def get_buildings():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM buildings ORDER BY name').fetchall()]

def get_building(bldg_num):
    with get_conn() as conn:
        r = conn.execute('SELECT * FROM buildings WHERE bldg_num=?', (str(bldg_num),)).fetchone()
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
            (data['bldg_num'], data['building_name'], data['district'],
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
                     (data['inspection_date'], data['bldg_num']))
        conn.commit()
        return insp_id

def get_inspections(bldg_num=None):
    with get_conn() as conn:
        if bldg_num:
            rows = conn.execute('SELECT * FROM inspections WHERE bldg_num=? ORDER BY inspection_date DESC', (str(bldg_num),)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM inspections ORDER BY created_at DESC').fetchall()
        return [dict(r) for r in rows]

def get_dashboard_stats():
    with get_conn() as conn:
        total = conn.execute('SELECT COUNT(*) FROM buildings').fetchone()[0]
        init_dev = conn.execute('SELECT SUM(init_devices) FROM buildings').fetchone()[0] or 0
        saved = conn.execute('SELECT COUNT(*) FROM inspections').fetchone()[0]

        schedule_rows = [dict(r) for r in conn.execute(
            'SELECT month, district, status, inspection_date FROM schedule'
        ).fetchall()]
        scheduled = len(schedule_rows)
        complete = sum(1 for r in schedule_rows if r.get('status') == 'Complete')
        overdue = sum(1 for r in schedule_rows if is_schedule_overdue(r))

        month_counts = {m: {'month': m, 'done': 0, 'total': 0} for m in MONTHS_LIST}
        for r in schedule_rows:
            month = r.get('month')
            if month not in month_counts:
                month_counts[month] = {'month': month, 'done': 0, 'total': 0}
            month_counts[month]['total'] += 1
            if r.get('status') == 'Complete':
                month_counts[month]['done'] += 1

        dist_counts = {}
        for r in schedule_rows:
            district = canonicalize_district(r.get('district'))
            if not district:
                continue
            dist_counts[district] = dist_counts.get(district, 0) + 1

        by_dist = [{'district': k, 'cnt': v} for k, v in sorted(dist_counts.items(), key=lambda kv: (-kv[1], kv[0]))]

        return {
            'total_buildings': total,
            'scheduled': scheduled,
            'complete': complete,
            'overdue': overdue,
            'saved_reports': saved,
            'init_devices': int(init_dev),
            'by_month': [month_counts[m] for m in MONTHS_LIST] + [v for k, v in month_counts.items() if k not in MONTHS_LIST],
            'by_district': by_dist,
        }

def refresh_overdue_statuses():
    """Recalculate overdue status using inspection_date when available, with month fallback."""
    today = date.today()
    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute(
            'SELECT id, month, status, inspection_date FROM schedule'
        ).fetchall()]
        for row in rows:
            status = str(row.get('status') or '').strip()
            if status in ('Complete', 'Construction'):
                continue
            new_status = 'Overdue' if is_schedule_overdue(row, today=today) else 'Pending'
            if status != new_status:
                conn.execute('UPDATE schedule SET status=? WHERE id=?', (new_status, row['id']))
        conn.commit()

def get_inspection(insp_id):

    with get_conn() as conn:
        r = conn.execute('SELECT * FROM inspections WHERE id=?', (insp_id,)).fetchone()
        return dict(r) if r else None

def delete_inspection(insp_id):
    with get_conn() as conn:
        conn.execute('DELETE FROM deficiencies WHERE inspection_id=?', (insp_id,))
        conn.execute('DELETE FROM inspections WHERE id=?', (insp_id,))
        conn.commit()

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
        conn.execute(f'UPDATE buildings SET {sets} WHERE bldg_num=?', vals + [str(bldg_num)])
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
