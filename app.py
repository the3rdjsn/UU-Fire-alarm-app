import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json, os, sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(__file__))
import db_supabase as db
from db_config import validate_db_config, get_db_mode
def get_local_building_image(bldg_num):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        images_dir = os.path.join(base_dir, "images")

        target = str(bldg_num).split(".")[0].strip()

        for ext in ["png", "jpg", "jpeg", "webp"]:
            path = os.path.join(images_dir, f"{target}.{ext}")
            if os.path.exists(path):
                return path

        return None
    except:
        return None


# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="UofU Fire Alarm Management",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── THEME / CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Core palette */
:root {
    --red: #CC2929;
    --dark: #1a1a1a;
    --card-bg: #ffffff;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #1a1a1a !important;
}
[data-testid="stSidebar"] * {
    color: #e0e0e0 !important;
}
[data-testid="stSidebar"] .stRadio label {
    padding: 6px 12px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(204,41,41,0.15);
}
[data-testid="stSidebar"] hr {
    border-color: #333 !important;
}

/* Header */
.uu-header {
    background: linear-gradient(135deg, #CC2929 0%, #9E1F1F 100%);
    padding: 16px 24px;
    border-radius: 10px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 24px;
    box-shadow: 0 2px 12px rgba(158,31,31,0.4);
}
.uu-header h1 {
    color: white !important;
    font-size: 22px !important;
    font-weight: 800 !important;
    margin: 0 !important;
    font-family: 'Segoe UI', sans-serif;
}
.uu-header p {
    color: rgba(255,255,255,0.75);
    font-size: 12px;
    margin: 2px 0 0 0;
}

/* Metric cards */
.metric-card {
    background: white;
    border: 1px solid #e8e8e8;
    border-radius: 12px;
    padding: 20px;
    border-left: 4px solid var(--accent, #CC2929);
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.metric-card .label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #888;
    margin-bottom: 6px;
}
.metric-card .value {
    font-size: 32px;
    font-weight: 800;
    color: var(--accent, #CC2929);
    line-height: 1;
}
.metric-card .sub {
    font-size: 11px;
    color: #aaa;
    margin-top: 4px;
}

/* Status badges */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
}
.badge-green  { background:#dcfce7; color:#166534; }
.badge-red    { background:#fee2e2; color:#991b1b; }
.badge-yellow { background:#fef9c3; color:#854d0e; }
.badge-blue   { background:#dbeafe; color:#1e40af; }
.badge-gray   { background:#f3f4f6; color:#6b7280; }

/* Section titles */
.section-title {
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #CC2929;
    border-bottom: 2px solid #CC2929;
    padding-bottom: 6px;
    margin-bottom: 16px;
}

/* Info grid in inspection report */
.info-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 16px;
}
.info-item { padding: 10px 14px; background: #f9f9f9; border-radius: 8px; border-left: 3px solid #CC2929; }
.info-item .lbl { font-size: 10px; color: #888; text-transform: uppercase; font-weight: 600; letter-spacing: 0.06em; }
.info-item .val { font-size: 14px; color: #1a1a1a; font-weight: 600; margin-top: 2px; }

/* Print button */
.print-btn {
    background: #CC2929;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 8px;
    font-weight: 700;
    cursor: pointer;
    width: 100%;
}

/* Tables */
.stDataFrame { border-radius: 8px; overflow: hidden; }
thead tr th { background: #1a1a1a !important; color: white !important; }

/* Overdue row highlight - applied via pandas styling */
</style>
""", unsafe_allow_html=True)

# ── INIT DB ──────────────────────────────────────────────────────────────────
@st.cache_resource
def init():
    mode = validate_db_config()
    app_dir = os.path.dirname(os.path.abspath(__file__))
    def load_json(name):
        local = os.path.join(app_dir, name)
        fallback = os.path.join('/tmp', name)
        path = local if os.path.exists(local) else fallback
        with open(path) as f:
            return json.load(f)
    buildings = load_json('buildings_clean.json')
    schedule = load_json('schedule_clean.json')
    devices = load_json('device_rows.json')
    db.init_db(buildings, schedule, devices)
    return mode

active_db_mode = init()


LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")

# Load logos as base64 — horizontal for headers/sidebar, vertical for print
def _load_logo_b64(fname):
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
    if os.path.exists(p):
        with open(p) as _f: return _f.read().strip()
    return ""

# logo_hrz_b64.txt  = horizontal logo on dark-red bg  → page headers
# logo_vert_b64.txt = vertical logo on white bg        → print report
# logo_b64.txt      = horizontal logo on dark bg       → sidebar
LOGO_B64        = _load_logo_b64("logo_dark_b64.txt")   # page headers (red bg) - white text
LOGO_B64_PRINT  = _load_logo_b64("logo_light_b64.txt")  # print report (white bg) - dark text
LOGO_HEADER_B64 = LOGO_B64                             # alias for header refs

MONTHS = ['All','January','February','March','April','May','June',
          'July','August','September','October','November','December']
MONTHS_NO_ALL = MONTHS[1:]

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, use_container_width=True)
    else:
        st.markdown("**DEPARTMENT OF FIRE SYSTEMS**")
    st.caption("Management System · 2026")
    st.divider()

    NAV_OPTIONS = [
        "📊  Dashboard",
        "📅  Schedule",
        "🏢  Buildings",
        "✏️  Edit Building",
        "📋  New Inspection",
        "📁  Inspection History",
        "🔍  Device Inventory",
        "🖨️  Print Report",
    ]

    # Programmatic navigation: set 'nav_target' before rerun to jump to a page
    if 'nav_target' in st.session_state:
        target = st.session_state.pop('nav_target')
        if target in NAV_OPTIONS:
            st.session_state['nav_radio'] = target

    page = st.radio("Navigation", NAV_OPTIONS,
                    key='nav_radio',
                    label_visibility="collapsed")



st.caption(f"Database mode: {active_db_mode}")

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊  Dashboard":
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>Fire Alarm Management Dashboard</h1>
          <p>University of Utah · Facilities Management · 2026 Inspection Program</p>
        </div>
    </div>''', unsafe_allow_html=True)

    stats = db.get_dashboard_stats()
    done = stats.get("complete", stats.get("inspections_complete", 0))
    scheduled = stats.get("scheduled", 0)
    done_pct = round(done / scheduled * 100) if scheduled else 0

    # Metric cards
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""<div class="metric-card" style="--accent:#CC2929">
            <div class="label">Total Systems</div>
            <div class="value">{stats['total_systems']}</div>
            <div class="sub">Buildings monitored</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card" style="--accent:#166534">
            <div class="label">Inspections Complete</div>
            <div class="value" style="color:#166534">{stats['complete']}</div>
            <div class="sub">of {stats['scheduled']} scheduled · {done_pct}%</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        color = '#991b1b' if stats['overdue'] > 0 else '#888'
        st.markdown(f"""<div class="metric-card" style="--accent:{color}">
            <div class="label">Overdue</div>
            <div class="value" style="color:{color}">{stats['overdue']}</div>
            <div class="sub">Past scheduled date</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card" style="--accent:#1e40af">
            <div class="label">Initiating Devices</div>
            <div class="value" style="color:#1e40af">{stats['init_devices']:,}</div>
            <div class="sub">Campus-wide total</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""<div class="metric-card" style="--accent:#854d0e">
            <div class="label">Reports Saved</div>
            <div class="value" style="color:#854d0e">{stats['reports_saved']}</div>
            <div class="sub">This cycle</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown('<div class="section-title">Monthly Inspection Progress</div>', unsafe_allow_html=True)
        month_order = {m: i for i, m in enumerate(MONTHS_NO_ALL)}
        month_data = {r['month']: r for r in stats['by_month']}
        months_plot = MONTHS_NO_ALL
        done_vals  = [month_data.get(m, {}).get('done', month_data.get(m, {}).get('complete', 0)) for m in months_plot]
        total_vals = [month_data.get(m, {}).get('total', 0) for m in months_plot]
        remain_vals = [t - d for t, d in zip(total_vals, done_vals)]
        cur_month = datetime.now().strftime('%B')

        colors_done   = ['#22c55e' for _ in done_vals]  # single green for all complete
        colors_remain = ['#fbbf24' if m == cur_month else '#CC2929' for m in months_plot]

        fig = go.Figure()
        fig.add_trace(go.Bar(name='Complete', x=months_plot, y=done_vals,
                             marker_color=colors_done, text=done_vals,
                             textposition='inside', textfont=dict(color='white', size=10)))
        fig.add_trace(go.Bar(name='Remaining', x=months_plot, y=remain_vals,
                             marker_color=colors_remain, text=remain_vals,
                             textposition='inside', textfont=dict(color='white', size=10)))
        fig.update_layout(
            barmode='stack', height=280,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation='h', y=-0.15),
            plot_bgcolor='white', paper_bgcolor='white',
            xaxis=dict(tickfont=dict(size=10)),
            yaxis=dict(showgrid=True, gridcolor='#f0f0f0')
        )
        st.plotly_chart(fig, use_container_width=True)

        # Upcoming this month
        st.markdown(f'<div class="section-title">Upcoming in {cur_month}</div>', unsafe_allow_html=True)
        upcoming = [s for s in db.get_schedule(cur_month) if s['status'] != 'Complete'][:10]
        if upcoming:
            up_df = pd.DataFrame([{
                'Building': s['building_name'],
                'District': s['district'],
                'Date': s['inspection_date'] or '—',
                'Est Hrs': s['est_hours'] or '—',
                'Status': s['status']
            } for s in upcoming])
            st.dataframe(up_df, use_container_width=True, hide_index=True,
                        column_config={'Status': st.column_config.TextColumn(width='small')})
        else:
            st.info(f"No pending inspections in {cur_month}")

    with col_right:
        st.markdown('<div class="section-title">By District</div>', unsafe_allow_html=True)
        dist_data = [(r['district'], r['cnt']) for r in stats['by_district']
                     if r['district'] and isinstance(r['district'], str) and len(r['district']) < 30]
        if dist_data:
            fig2 = go.Figure(go.Bar(
                x=[d[1] for d in dist_data],
                y=[d[0] for d in dist_data],
                orientation='h',
                marker_color='#CC2929',
                text=[d[1] for d in dist_data],
                textposition='outside'
            ))
            fig2.update_layout(
                height=320, margin=dict(l=0, r=30, t=0, b=0),
                plot_bgcolor='white', paper_bgcolor='white',
                xaxis=dict(showgrid=False), yaxis=dict(tickfont=dict(size=10))
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown('<div class="section-title">Panel Types</div>', unsafe_allow_html=True)
        buildings = db.get_buildings()
        panel_counts = {}
        for b in buildings:
            p = b.get('panel_type') or 'Unknown'
            panel_counts[p] = panel_counts.get(p, 0) + 1
        panel_counts = {k: v for k, v in panel_counts.items() if k != 'Unknown'}
        pcolors = {'E-3':'#1e40af','E-3 VOICE':'#166534','S-3':'#6d28d9',
                   '7100':'#854d0e','7200':'#c2410c','Simplex':'#CC2929'}
        fig3 = go.Figure(go.Pie(
            labels=list(panel_counts.keys()),
            values=list(panel_counts.values()),
            marker_colors=[pcolors.get(k,'#888') for k in panel_counts],
            textinfo='label+percent', textfont_size=10,
            hole=0.4
        ))
        fig3.update_layout(height=220, margin=dict(l=0,r=0,t=0,b=0),
                           showlegend=False, paper_bgcolor='white')
        st.plotly_chart(fig3, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# SCHEDULE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📅  Schedule":
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>2026 Inspection Schedule</h1>
          <p>Click any row to update status · Changes save instantly to the database</p>
        </div>
    </div>''', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        month_filter = st.selectbox("Filter by Month", MONTHS, key='sched_month')
    with col2:
        status_filter = st.selectbox("Filter by Status",
            ['All','Complete','Pending','Overdue','Construction','In Progress'], key='sched_status')
    with col3:
        all_districts = sorted(set(
            s.get('district','') for s in db.get_schedule()
            if s.get('district') and len(s.get('district','')) < 30))
        dist_filter = st.selectbox("Filter by District",
            ['All'] + all_districts, key='sched_dist')
    with col4:
        search_sched = st.text_input("Search Building", placeholder="Name or #…", key='sched_search')

    rows = db.get_schedule(month_filter)
    if status_filter != 'All':
        rows = [r for r in rows if r['status'] == status_filter]
    if dist_filter != 'All':
        rows = [r for r in rows if r.get('district','').strip().lower() == dist_filter.strip().lower()]
    if search_sched:
        q = search_sched.lower()
        rows = [r for r in rows if q in r.get('building_name','').lower() or q in str(r.get('bldg_num','')).lower()]

    # Summary pills
    done  = sum(1 for r in rows if r['status'] == 'Complete')
    over  = sum(1 for r in rows if r['status'] == 'Overdue')
    pend  = sum(1 for r in rows if r['status'] == 'Pending')
    hours = sum(float(r.get('est_hours') or 0) for r in rows)
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Showing", len(rows), "inspections")
    p2.metric("Complete", done)
    p3.metric("Overdue", over, delta=f"-{over}" if over else None, delta_color="inverse")
    p4.metric("Est Hours", f"{hours:.0f}h")

    st.divider()

    # Editable table
    for r in rows:
        bname = r['building_name']
        status = r['status']
        badge_class = {'Complete':'badge-green','Overdue':'badge-red',
                       'Pending':'badge-yellow','Construction':'badge-blue'}.get(status,'badge-gray')

        with st.expander(
            f"**{bname}** — {r['month']} | {r.get('inspection_date') or 'TBD'} | "
            f"{r.get('est_hours','?')}h  [{status}]",
            expanded=False
        ):
            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
            with c1:
                st.write(f"**District:** {r.get('district','—')}")
                st.write(f"**Address:** {r.get('address','—')}")
            with c2:
                st.write(f"**Scheduled Date:** {r.get('inspection_date') or '—'}")
                st.write(f"**Est. Hours:** {r.get('est_hours','—')}")
            with c3:
                new_status = st.selectbox("Status",
                    ['Pending','In Progress','Complete','Overdue','Construction'],
                    index=['Pending','In Progress','Complete','Overdue','Construction'].index(
                        status if status in ['Pending','In Progress','Complete','Overdue','Construction'] else 'Pending'),
                    key=f"status_{r['id']}")
                uploaded = st.selectbox("Uploaded CMS",['No','Yes'],
                    index=0 if r.get('uploaded_cms') != 'Yes' else 1,
                    key=f"cms_{r['id']}")
            with c4:
                date_done = st.date_input("Date Completed",
                    value=datetime.strptime(r['date_completed'], '%Y-%m-%d').date()
                          if r.get('date_completed') else None,
                    key=f"donedate_{r['id']}")
                if st.button("💾 Save", key=f"save_{r['id']}", type="primary"):
                    db.update_schedule_status(
                        r['id'], new_status,
                        date_done.isoformat() if date_done else None,
                        None, uploaded)
                    st.success("Saved!")
                    st.rerun()

            notes_val = st.text_area("Notes", value=r.get('notes',''),
                                     key=f"notes_{r['id']}", height=60)
            if st.button("Save Notes", key=f"savenotes_{r['id']}"):
                db.update_schedule_status(r['id'], new_status, None, notes_val, None)
                st.success("Notes saved")
                st.rerun()

            if st.button("📋 Start Inspection Report", key=f"insp_{r['id']}", type="primary"):
                st.session_state['prefill_bldg'] = str(r['bldg_num']).split('.')[0]
                st.session_state['nav_target'] = '📋  New Inspection'
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# BUILDINGS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏢  Buildings":
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>Building Directory</h1>
          <p>164 buildings · Panel info · Device counts · Network details</p>
        </div>
    </div>''', unsafe_allow_html=True)

    buildings = db.get_buildings()

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        search = st.text_input("🔍  Search by name, number, district, panel type…", key='bldg_search')
    with col2:
        dist_f = st.selectbox("District", ['All'] + sorted(set(
            b['district'] for b in buildings if b.get('district') and len(b.get('district',''))<30)))
    with col3:
        panel_f = st.selectbox("Panel Type", ['All'] + sorted(set(
            b['panel_type'] for b in buildings if b.get('panel_type') and isinstance(b.get('panel_type'),str))))

    # Sort numerically (1, 2, 3... not 1, 10, 11...)
    def _bldg_sort_key(b):
        n = str(b.get('bldg_num') or '')
        try: return (0, int(n))
        except: return (1, n)

    filtered = sorted(buildings, key=_bldg_sort_key)
    if search:
        q = search.lower()
        filtered = [b for b in filtered if q in str(b.get('name','')).lower()
                    or q in str(b.get('bldg_num','')).lower()
                    or q in str(b.get('district','')).lower()
                    or q in str(b.get('panel_type','')).lower()
                    or q in str(b.get('focalpoint_name','')).lower()]
    if dist_f != 'All':
        filtered = [b for b in filtered if b.get('district') == dist_f]
    if panel_f != 'All':
        filtered = [b for b in filtered if b.get('panel_type') == panel_f]

    st.write(f"**{len(filtered)}** buildings")

    def _i(v):
        try: return int(float(v)) if v not in (None, '') else ''
        except: return v

    # Show as dataframe
    df = pd.DataFrame([{
        '#': b['bldg_num'],
        'Building': b['name'],
        'District': b['district'],
        'Panel': b['panel_type'],
        'Age (Yrs)': _i(b['age']),
        'Insp Month': b['inspection_month'],
        'Init Dev': _i(b['init_devices']),
        'Nodes': _i(b['nodes']),
        'Gateway': b['gateway'],
        'Priority': _i(b['replacement_priority']),
    } for b in filtered])

    def color_age(val):
        try:
            v = int(val)
            if v >= 20: return 'color: #991b1b; font-weight: bold'
            if v >= 15: return 'color: #c2410c; font-weight: bold'
            if v >= 10: return 'color: #854d0e'
        except: pass
        return ''

    try:
        if 'Age (Yrs)' in df.columns and df['Age (Yrs)'].notna().any():
            try:
                styled = df.style.map(color_age, subset=['Age (Yrs)'])
            except AttributeError:
                styled = df.style.applymap(color_age, subset=['Age (Yrs)'])
        else:
            styled = df.style
    except Exception:
        styled = df.style
    st.dataframe(styled, use_container_width=True, hide_index=True, height=500)

    st.divider()
    st.markdown('<div class="section-title">Building Detail</div>', unsafe_allow_html=True)
    bnum = st.selectbox("Select building for full details",
                        [f"{b['bldg_num']} — {b['name']}" for b in filtered])
    if bnum:
        sel_num = bnum.split(' — ')[0]
        b = db.get_building(sel_num)
        if b:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown('<div class="section-title">Building Info</div>', unsafe_allow_html=True)
                for lbl, val in [('Address', b.get('address')), ('City/State', f"{b.get('city','')}, {b.get('state','')} {b.get('zip','')}"),
                                  ('Built', b.get('built')), ('Sq Ft', f"{(b.get('sq_ft') or 0):,}"),
                                  ('District', b.get('district')), ('Auxiliary', b.get('aux'))]:
                    st.write(f"**{lbl}:** {val or '—'}")
            with c2:
                st.markdown('<div class="section-title">Panel & Network</div>', unsafe_allow_html=True)
                for lbl, val in [('Panel Type', b.get('panel_type')), ('Year Installed', b.get('year_installed')),
                                  ('System Age', f"{b.get('age','—')} years"), ('Gateway IP', b.get('gateway_ip')),
                                  ('ANX IP', b.get('anx_ip')), ('FocalPoint Name', b.get('focalpoint_name')),
                                  ('Panel Location', b.get('panel_location')), ('AIM Asset #', b.get('aim_asset'))]:
                    st.write(f"**{lbl}:** {val or '—'}")
            with c3:
                st.markdown('<div class="section-title">Device Counts</div>', unsafe_allow_html=True)
                devs = {
                    'Smoke Detectors': b.get('smoke'),
                    'Heat Detectors': b.get('heat'),
                    'Pull Stations': b.get('pull'),
                    'Duct Detectors': b.get('duct'),
                    'Initiating (Total)': b.get('init_devices'),
                    'Notification (Total)': b.get('notif_devices'),
                    'Transponders': b.get('transponders'),
                    'Nodes': b.get('nodes'),
                }
                for k, v in devs.items():
                    st.write(f"**{k}:** {int(v) if v else '—'}")

            # Inspection history for building
            hist = db.get_inspections(sel_num)
            if hist:
                st.markdown('<div class="section-title">Inspection History</div>', unsafe_allow_html=True)
                hist_df = pd.DataFrame([{
                    'Date': h['inspection_date'],
                    'Result': h['result'],
                    '% Tested': f"{h['pct_tested']:.0f}%",
                    'Deficiencies': len(json.loads(h['deficiencies'] or '[]')),
                    'WO#': h['work_order'],
                    'Inspector': h['inspector_name']
                } for h in hist])
                st.dataframe(hist_df, use_container_width=True, hide_index=True)

            ba1, ba2 = st.columns(2)
            with ba1:
                if st.button("📋 Start Inspection", key=f'bldg_insp_{sel_num}', use_container_width=True, type="primary"):
                    st.session_state['prefill_bldg'] = sel_num
                    st.session_state['nav_target'] = '📋  New Inspection'
                    st.rerun()
            with ba2:
                if st.button("✏️ Edit Building Info", key=f'bldg_edit_{sel_num}', use_container_width=True):
                    st.session_state['edit_bldg_num'] = sel_num
                    st.session_state['nav_target'] = '✏️  Edit Building'
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# NEW INSPECTION REPORT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋  New Inspection":
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>Fire Alarm Management Dashboard</h1>
          <p>University of Utah · Facilities Management · 2026 Inspection Program</p>
        </div>
    </div>''', unsafe_allow_html=True)

    buildings = db.get_buildings()
    # Store bldg_num as the key — not the label — so it never drifts on rerun
    bldg_nums   = [b["bldg_num"] for b in buildings]
    bldg_labels = [f"{b['bldg_num']} — {b['name']}" for b in buildings]

    # Handle prefill from schedule/buildings page
    if "prefill_bldg" in st.session_state:
        st.session_state["report_bldg_num"] = st.session_state.pop("prefill_bldg")

    if "report_bldg_num" not in st.session_state:
        st.session_state["report_bldg_num"] = bldg_nums[0]

    cur_num = st.session_state["report_bldg_num"]
    cur_idx = bldg_nums.index(cur_num) if cur_num in bldg_nums else 0

    chosen_label = st.selectbox(
        "🏢  Select Building", bldg_labels,
        index=cur_idx,
        key="report_bldg_select",
        help="All fields below auto-populate from the building database")

    # Always sync session_state to current selection — survives every rerun
    sel_num = bldg_nums[bldg_labels.index(chosen_label)]
    st.session_state["report_bldg_num"] = sel_num
    b = db.get_building(sel_num)

    if b:
        # ── AUTO-POPULATED BUILDING INFO ──────────────────────────────────────
        st.markdown('<div class="section-title">Building Information — Auto-populated</div>',
                    unsafe_allow_html=True)

        info_cols = st.columns(4)
        info_fields = [
            ('Building Name', b.get('name','—')),
            ('Building #', b.get('bldg_num','—')),
            ('District', b.get('district','—')),
            ('Address', b.get('address','—')),
            ('Panel Type', b.get('panel_type','—')),
            ('Year Installed', b.get('year_installed','—')),
            ('System Age', f"{b.get('age','—')} years"),
            ('Panel Location', b.get('panel_location','—')),
            ('Gateway IP', b.get('gateway_ip','—')),
            ('ANX IP', b.get('anx_ip','—')),
            ('FocalPoint Name', b.get('focalpoint_name','—')),
            ('AIM Asset #', b.get('aim_asset','—')),
        ]
        for i, (lbl, val) in enumerate(info_fields):
            with info_cols[i % 4]:
                st.markdown(f"""<div class="info-item">
                    <div class="lbl">{lbl}</div>
                    <div class="val">{val}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── INSPECTION DETAILS ─────────────────────────────────────────────────
        st.markdown('<div class="section-title">Inspection Details</div>', unsafe_allow_html=True)
        d1, d2, d3, d4 = st.columns(4)
        with d1:
            insp_date = st.date_input("Date of Inspection", value=date.today())
        with d2:
            work_order = st.text_input("Work Order #", placeholder="WO-")
        with d3:
            insp_type = st.selectbox("Inspection Type",
                ["Annual Inspection", "Special Inspection/Audit", "New Panel Inspection"])
        with d4:
            result = st.selectbox("Overall Result", ["PASS", "FAIL", "PARTIAL — Deficiencies Noted"])
        inspector = st.text_input("Inspector Name", placeholder="Your name")

        # ── AES RADIO TEST ─────────────────────────────────────────────────────
        st.markdown('<div class="section-title">AES Radio Test</div>', unsafe_allow_html=True)
        aes_cols = st.columns(7)
        aes_labels = ['Alarm','Supervisory','Trouble','Waterflow','Tamper','Duct','Fire Ext']
        aes_vals = {}
        for i, lbl in enumerate(aes_labels):
            with aes_cols[i]:
                aes_vals[lbl] = st.selectbox(lbl, ['PASS','FAIL','N/A','NOT TESTED'],
                                              key=f'aes_{lbl}')

        # ── DEVICE TESTING ─────────────────────────────────────────────────────
        st.markdown('<div class="section-title">Device Testing Results</div>', unsafe_allow_html=True)

        dev_config = [
            ('PS',    'Pull Stations',      b.get('pull') or 0),
            ('SD',    'Smoke Detectors',    b.get('smoke') or 0),
            ('HD',    'Heat Detectors',     b.get('heat') or 0),
            ('DD',    'Duct Detectors',     b.get('duct') or 0),
            ('WF',    'Waterflow Switches', 0),
            ('TS',    'Tamper Switches',    0),
            ('NOTIF', 'Notification Devices', int(b.get('notif_devices') or 0)),
            ('Trans', 'Transponders',       b.get('transponders') or 0),
        ]

        dev_tested = {}
        total_init = int(b.get('init_devices') or 0)

        # Header
        hc = st.columns([1, 3, 1.5, 1.5, 1.5, 2])
        for h, col in zip(['Code','Device Type','Total','Tested','Remaining','Status'], hc):
            col.markdown(f"**{h}**")

        total_tested_sum = 0
        total_count_sum = 0
        for code, label, default_total in dev_config:
            row_cols = st.columns([1, 3, 1.5, 1.5, 1.5, 2])
            with row_cols[0]:
                st.markdown(f"`{code}`")
            with row_cols[1]:
                st.write(label)
            with row_cols[2]:
                total = st.number_input("", min_value=0, value=int(default_total),
                                        key=f'tot_{code}', label_visibility='collapsed')
            with row_cols[3]:
                tested = st.number_input("", min_value=0, value=int(default_total),
                                         key=f'tst_{code}', label_visibility='collapsed')
            with row_cols[4]:
                remaining = max(0, total - tested)
                color = 'red' if remaining > 0 else 'green'
                st.markdown(f"<span style='color:{color};font-weight:bold'>{remaining}</span>",
                            unsafe_allow_html=True)
            with row_cols[5]:
                options = ['TESTED','PARTIAL','NOT TESTED','N/A','CONSTRUCTION']
                status_default = 'TESTED' if tested == total and total > 0 else ('PARTIAL' if tested > 0 else 'NOT TESTED')
                dev_status = st.selectbox("", options,
                    index=options.index(status_default), key=f'dstat_{code}',
                    label_visibility='collapsed')
            dev_tested[code] = {'total': total, 'tested': tested, 'status': dev_status}
            if code not in ('NOTIF', 'Trans'):
                total_tested_sum += tested
                total_count_sum += total

        # Progress bar
        pct = (total_tested_sum / total_count_sum * 100) if total_count_sum > 0 else 0
        bar_color = '#22c55e' if pct >= 90 else ('#f97316' if pct >= 50 else '#CC2929')
        st.markdown(f"""
        <div style="margin:12px 0">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                <span style="font-size:12px;font-weight:600;color:#555">Overall % Tested</span>
                <span style="font-size:13px;font-weight:800;color:{bar_color}">{pct:.0f}%</span>
            </div>
            <div style="background:#e5e7eb;border-radius:99px;height:8px">
                <div style="background:{bar_color};width:{pct:.0f}%;height:8px;border-radius:99px;transition:width .3s"></div>
            </div>
        </div>""", unsafe_allow_html=True)

        # ── FOCALPOINT DEVICE LIST ─────────────────────────────────────────────
        fp_name = b.get('focalpoint_name','')
        fp_devices = db.get_devices_for_building(fp_name, b.get('name',''))

        if fp_devices:
            with st.expander(f"📍 FocalPoint Device List ({len(fp_devices):,} points)", expanded=False):
                fp_search = st.text_input("Filter devices", key='fp_dev_search',
                                          placeholder="Search type, point, description…")
                fp_filtered = fp_devices
                if fp_search:
                    q = fp_search.lower()
                    fp_filtered = [d for d in fp_devices if q in (d.get('type','') or '').lower()
                                   or q in (d.get('point','') or '').lower()
                                   or q in (d.get('description','') or '').lower()]

                # Pagination
                FP_PAGE = 30
                fp_total = len(fp_filtered)
                fp_pages = max(1, (fp_total + FP_PAGE - 1) // FP_PAGE)
                if 'fp_page' not in st.session_state:
                    st.session_state['fp_page'] = 0
                # Reset page when filter changes
                fp_page = min(st.session_state.get('fp_page', 0), fp_pages - 1)

                pc1, pc2, pc3 = st.columns([1, 2, 1])
                with pc1:
                    if st.button("◀ Prev", key='fp_prev', disabled=(fp_page == 0)):
                        st.session_state['fp_page'] = fp_page - 1
                        st.rerun()
                with pc2:
                    st.caption(f"Page {fp_page+1}/{fp_pages} — {fp_total:,} devices")
                with pc3:
                    if st.button("Next ▶", key='fp_next', disabled=(fp_page >= fp_pages - 1)):
                        st.session_state['fp_page'] = fp_page + 1
                        st.rerun()

                page_devices = fp_filtered[fp_page*FP_PAGE : (fp_page+1)*FP_PAGE]

                # Header row
                hc = st.columns([1, 2, 4, 1.5])
                for h, col in zip(['Type','Point','Description','Result'], hc):
                    col.markdown(f"**{h}**")
                st.divider()

                # FP device results — stored in session_state[fp_results_key]
                # fp_ver tracks a version number; Mark All increments it so
                # widget keys change, forcing Streamlit to re-init from fp_res.
                fp_results_key = f'fp_results_{sel_num}'
                fp_ver_key     = f'fp_ver_{sel_num}'
                if fp_results_key not in st.session_state:
                    st.session_state[fp_results_key] = {}
                if fp_ver_key not in st.session_state:
                    st.session_state[fp_ver_key] = 0

                # Mark All buttons — bump version so widget keys change on rerun
                ma1, ma2, ma3, ma4 = st.columns([1.2, 1.2, 1.2, 3])
                with ma1:
                    if st.button("✅ Mark All Pass", key=f'all_pass_{sel_num}', use_container_width=True):
                        st.session_state[fp_results_key] = {str(gi): 'Pass' for gi in range(len(fp_devices))}
                        st.session_state[fp_ver_key] += 1
                        st.rerun()
                with ma2:
                    if st.button("❌ Mark All Fail", key=f'all_fail_{sel_num}', use_container_width=True):
                        st.session_state[fp_results_key] = {str(gi): 'Fail' for gi in range(len(fp_devices))}
                        st.session_state[fp_ver_key] += 1
                        st.rerun()
                with ma3:
                    if st.button("🔄 Clear All", key=f'all_clear_{sel_num}', use_container_width=True):
                        st.session_state[fp_results_key] = {}
                        st.session_state[fp_ver_key] += 1
                        st.rerun()

                fp_res = st.session_state[fp_results_key]
                fp_ver = st.session_state[fp_ver_key]

                with ma4:
                    pass_c  = sum(1 for v in fp_res.values() if v == 'Pass')
                    fail_c  = sum(1 for v in fp_res.values() if v == 'Fail')
                    na_c    = sum(1 for v in fp_res.values() if v == 'N/A')
                    marked  = pass_c + fail_c + na_c
                    st.markdown(
                        f'<div style="padding:8px 0;font-size:12px">'
                        f'<span style="color:#166534;font-weight:700">{pass_c} Pass</span> &nbsp;·&nbsp; '
                        f'<span style="color:#991b1b;font-weight:700">{fail_c} Fail</span> &nbsp;·&nbsp; '
                        f'<span style="color:#888">{na_c} N/A</span> &nbsp;·&nbsp; '
                        f'<span style="color:#555">{len(fp_filtered)-marked} unmarked of {len(fp_filtered)}</span></div>',
                        unsafe_allow_html=True)

                for di, d in enumerate(page_devices):
                    global_idx = fp_devices.index(d) if d in fp_devices else (fp_page * FP_PAGE + di)
                    item_key = str(global_idx)
                    cur_val = fp_res.get(item_key, '—')
                    opts = ['—','Pass','Fail','N/A']
                    rc = st.columns([1, 2, 4, 1.5])
                    with rc[0]:
                        st.markdown(f"`{d.get('type','—')}`")
                    with rc[1]:
                        st.caption(d.get('point','—'))
                    with rc[2]:
                        st.write(d.get('description','—') or '—')
                    with rc[3]:
                        # fp_ver in key forces widget to re-init when Mark All changes values
                        new_val = st.selectbox("", opts,
                            index=opts.index(cur_val) if cur_val in opts else 0,
                            key=f"fp_sel_{sel_num}_{fp_ver}_{item_key}",
                            label_visibility='collapsed')
                        # Always sync widget value back to fp_res (not just on change)
                        fp_res[item_key] = new_val

                # Persist the fully synced fp_res back to session_state
                st.session_state[fp_results_key] = fp_res

        # ── DEFICIENCIES ───────────────────────────────────────────────────────
        st.markdown('<div class="section-title">Deficiencies</div>', unsafe_allow_html=True)

        if 'deficiencies' not in st.session_state:
            st.session_state.deficiencies = []

        # Auto-populate deficiencies from failed FP devices
        fp_results_key = f'fp_results_{sel_num}'
        fp_res_cur = st.session_state.get(fp_results_key, {})
        if fp_res_cur and fp_devices:
            existing_points = {d.get('location','') for d in st.session_state.deficiencies}
            for idx_str, result in fp_res_cur.items():
                if result == 'Fail':
                    try:
                        dev = fp_devices[int(idx_str)]
                        point = str(dev.get('point', idx_str))
                        if point not in existing_points:
                            dtype = str(dev.get('type', ''))
                            desc  = str(dev.get('description', ''))
                            st.session_state.deficiencies.append({
                                'device':    dtype,
                                'location':  point,
                                'issue':     f"FAILED — {desc}" if desc else "FAILED",
                                'part':      '',
                                'corrected': 'No',
                            })
                            existing_points.add(point)
                    except (IndexError, ValueError):
                        pass

        col_add, col_clear = st.columns([1, 1])
        with col_add:
            if st.button("➕ Add Deficiency"):
                st.session_state.deficiencies.append(
                    {'device': '', 'location': '', 'issue': '', 'part': '', 'corrected': 'No'})
        with col_clear:
            if st.button("🔄 Sync Failed Devices", help="Re-pull all Fail results from FocalPoint list"):
                existing_points = set()
                st.session_state.deficiencies = []
                for idx_str, result in fp_res_cur.items():
                    if result == 'Fail':
                        try:
                            dev = fp_devices[int(idx_str)]
                            point = str(dev.get('point', idx_str))
                            if point not in existing_points:
                                dtype = str(dev.get('type', ''))
                                desc  = str(dev.get('description', ''))
                                st.session_state.deficiencies.append({
                                    'device':    dtype,
                                    'location':  point,
                                    'issue':     f"FAILED — {desc}" if desc else "FAILED",
                                    'part':      '',
                                    'corrected': 'No',
                                })
                                existing_points.add(point)
                        except (IndexError, ValueError):
                            pass
                st.rerun()

        for i, d in enumerate(st.session_state.deficiencies):
            with st.container():
                dc1, dc2, dc3, dc4, dc5, dc6 = st.columns([1, 2, 3, 2, 1, 0.5])
                with dc1:
                    d['device'] = st.text_input("Device", value=d['device'],
                                                key=f'def_dev_{i}', placeholder="PS / SD…")
                with dc2:
                    d['location'] = st.text_input("Location / Point", value=d['location'],
                                                  key=f'def_loc_{i}')
                with dc3:
                    d['issue'] = st.text_input("Issue Found", value=d['issue'],
                                               key=f'def_issue_{i}')
                with dc4:
                    d['part'] = st.text_input("Part # Required", value=d['part'],
                                              key=f'def_part_{i}')
                with dc5:
                    d['corrected'] = st.selectbox("Fixed?", ['No','Yes','Partial'],
                                                  key=f'def_fix_{i}')
                with dc6:
                    if st.button("✕", key=f'def_del_{i}'):
                        st.session_state.deficiencies.pop(i)
                        st.rerun()

        if not st.session_state.deficiencies:
            st.info("No deficiencies — click Add Deficiency if needed")

        # ── NOTES ──────────────────────────────────────────────────────────────
        st.markdown('<div class="section-title">Notes & Summary</div>', unsafe_allow_html=True)
        notes = st.text_area("", placeholder="Inspection notes, observations, system condition…",
                             height=100, label_visibility='collapsed')

        # ── SAVE ───────────────────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        s1, s2 = st.columns([1, 3])
        with s1:
            if st.button("💾  Save Inspection Report", type="primary", use_container_width=True):
                data = {
                    'bldg_num': b['bldg_num'], 'building_name': b['name'],
                    'district': b['district'], 'inspection_date': insp_date.isoformat(),
                    'work_order': work_order, 'inspection_type': insp_type,
                    'result': result, 'notes': notes, 'inspector_name': inspector,
                    'pct_tested': pct,
                    'ps_total': dev_tested['PS']['total'],   'ps_tested': dev_tested['PS']['tested'],
                    'sd_total': dev_tested['SD']['total'],   'sd_tested': dev_tested['SD']['tested'],
                    'hd_total': dev_tested['HD']['total'],   'hd_tested': dev_tested['HD']['tested'],
                    'dd_total': dev_tested['DD']['total'],   'dd_tested': dev_tested['DD']['tested'],
                    'wf_total': dev_tested['WF']['total'],   'wf_tested': dev_tested['WF']['tested'],
                    'ts_total': dev_tested['TS']['total'],   'ts_tested': dev_tested['TS']['tested'],
                    'notif_total': dev_tested['NOTIF']['total'], 'notif_tested': dev_tested['NOTIF']['tested'],
                    'trans_total': dev_tested['Trans']['total'], 'trans_tested': dev_tested['Trans']['tested'],
                    'aes_alarm': aes_vals.get('Alarm','PASS'),
                    'aes_supv':  aes_vals.get('Supervisory','PASS'),
                    'aes_trouble': aes_vals.get('Trouble','PASS'),
                    'aes_wf':    aes_vals.get('Waterflow','PASS'),
                    'aes_tamper': aes_vals.get('Tamper','PASS'),
                    'aes_duct':  aes_vals.get('Duct','PASS'),
                    'aes_ext':   aes_vals.get('Fire Ext','PASS'),
                }
                insp_id = db.save_inspection(data, st.session_state.deficiencies)
                # Save FocalPoint device results
                fp_results_key = f'fp_results_{sel_num}'
                fp_res = st.session_state.get(fp_results_key, {})
                if fp_res:
                    db.save_device_results(insp_id, fp_res)
                st.session_state.deficiencies = []
                st.session_state[fp_results_key] = {}
                st.success(f"✅ Report saved for **{b['name']}** — ID #{insp_id}")
                st.balloons()

        with s2:
            if st.button("🖨️  Preview & Print Report", use_container_width=True):
                fp_results_key = f'fp_results_{sel_num}'
                fp_ver_key     = f'fp_ver_{sel_num}'
                fp_ver_now     = st.session_state.get(fp_ver_key, 0)
                # Rebuild fp_res from actual widget values (most authoritative source)
                # Scan all fp_sel widget keys for this building + version
                widget_fp = {}
                for k, v in st.session_state.items():
                    if k.startswith(f'fp_sel_{sel_num}_{fp_ver_now}_') and v != '—':
                        item_idx = k.rsplit('_', 1)[-1]
                        widget_fp[item_idx] = v
                # Fall back to stored fp_res if no widget keys found (expander was closed)
                stored_fp = {k: v for k, v in st.session_state.get(fp_results_key, {}).items() if v != '—'}
                captured_fp = widget_fp if widget_fp else stored_fp
                st.session_state['print_report_data'] = {
                    'bldg': b, 'date': str(insp_date), 'wo': work_order,
                    'type': insp_type, 'result': result, 'inspector': inspector,
                    'aes': aes_vals, 'dev_tested': dev_tested,
                    'defs': list(st.session_state.get('deficiencies', [])),
                    'notes': notes, 'pct': pct,
                    'device_results': captured_fp,
                }
                st.session_state['nav_target'] = '🖨️  Print Report'
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# INSPECTION HISTORY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📁  Inspection History":
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>2026 Inspection Schedule</h1>
          <p>Click any row to update status · Changes save instantly to the database</p>
        </div>
    </div>''', unsafe_allow_html=True)

    inspections = db.get_inspections()
    if not inspections:
        st.info("No inspection reports saved yet. Complete an inspection from the **New Inspection** page.")
        st.stop()

    # Summary
    total = len(inspections)
    passes = sum(1 for i in inspections if 'PASS' in str(i.get('result','')))
    fails  = sum(1 for i in inspections if 'FAIL' in str(i.get('result','')))
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Reports", total)
    m2.metric("Pass", passes)
    m3.metric("Fail / Partial", total - passes)

    st.divider()

    for insp in inspections:
        result = insp.get('result','—')
        result_icon = '✅' if 'PASS' in str(result) else '❌' if 'FAIL' in str(result) else '⚠️'
        defs = json.loads(insp.get('deficiencies') or '[]')

        with st.expander(
            f"{result_icon} **{insp['building_name']}** — {insp['inspection_date']} — {result} — {insp['pct_tested']:.0f}% tested",
            expanded=False
        ):
            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                st.write(f"**District:** {insp.get('district','—')}")
                st.write(f"**Date:** {insp.get('inspection_date','—')}")
                st.write(f"**Type:** {insp.get('inspection_type','—')}")
                st.write(f"**WO#:** {insp.get('work_order','—')}")
                st.write(f"**Inspector:** {insp.get('inspector_name','—')}")
            with rc2:
                st.write("**Device Testing:**")
                for code, lbl in [('ps','Pull Stations'),('sd','Smoke'),('hd','Heat'),('dd','Duct')]:
                    tot = insp.get(f'{code}_total') or 0
                    tst = insp.get(f'{code}_tested') or 0
                    if tot: st.write(f"  {lbl}: {tst}/{tot}")
            with rc3:
                st.write("**AES Tests:**")
                for key, lbl in [('aes_alarm','Alarm'),('aes_supv','Supv'),('aes_trouble','Trouble')]:
                    v = insp.get(key,'—')
                    icon = '✅' if v=='PASS' else '❌'
                    st.write(f"  {icon} {lbl}: {v}")

            if defs:
                st.write(f"**Deficiencies ({len(defs)}):**")
                for d in defs:
                    part_str = f" (Part: {d['part']})" if d.get('part') else ''
                    st.write(f"  - [{d.get('device','')}] {d.get('location','')} -- {d.get('issue','')}{part_str}")

            if insp.get('notes'):
                st.write(f"**Notes:** {insp['notes']}")

            hb1, hb2, hb3 = st.columns([1, 1, 2])
            with hb1:
                if st.button("🖨️ Print Report", key=f"print_insp_{insp['id']}", use_container_width=True):
                    b_data = db.get_building(str(insp['bldg_num']))
                    dev_tested_hist = {
                        code: {'total': insp.get(f'{code.lower()}_total',0),
                               'tested': insp.get(f'{code.lower()}_tested',0),
                               'status': 'TESTED'}
                        for code in ['PS','SD','HD','DD','WF','TS','NOTIF','Trans']
                    }
                    aes_hist = {
                        'Alarm': insp.get('aes_alarm','—'),
                        'Supervisory': insp.get('aes_supv','—'),
                        'Trouble': insp.get('aes_trouble','—'),
                        'Waterflow': insp.get('aes_wf','—'),
                        'Tamper': insp.get('aes_tamper','—'),
                        'Duct': insp.get('aes_duct','—'),
                        'Fire Ext': insp.get('aes_ext','—'),
                    }
                    st.session_state['print_report_data'] = {
                        'bldg': b_data or {'name': insp['building_name'], 'bldg_num': insp['bldg_num'],
                                           'district': insp.get('district',''), 'address':'', 'city':'','state':'',
                                           'panel_type':'','year_installed':'','panel_location':'',
                                           'aim_asset':'','gateway_ip':'','focalpoint_name':''},
                        'date': insp['inspection_date'],
                        'wo': insp.get('work_order',''),
                        'type': insp.get('inspection_type','Annual Inspection'),
                        'result': insp.get('result','PASS'),
                        'inspector': insp.get('inspector_name',''),
                        'aes': aes_hist,
                        'dev_tested': dev_tested_hist,
                        'defs': json.loads(insp.get('deficiencies') or '[]'),
                        'notes': insp.get('notes',''),
                        'pct': insp.get('pct_tested', 0),
                        'device_results': {k:v for k,v in db.get_device_results(insp['id']).items() if v != '—'},
                    }
                    st.session_state['nav_target'] = '🖨️  Print Report'
                    st.rerun()
            with hb2:
                if st.button("✏️ Edit", key=f"edit_insp_{insp['id']}", use_container_width=True):
                    st.session_state['edit_insp_id'] = insp['id']
                    st.session_state['nav_target'] = '📋  New Inspection'
                    st.session_state['prefill_bldg'] = str(insp['bldg_num'])
                    st.rerun()
            with hb3:
                if st.button("🗑 Delete", key=f"del_insp_{insp['id']}", use_container_width=True):
                    db.delete_inspection(insp['id'])
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# DEVICE INVENTORY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔍  Device Inventory":
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>FocalPoint Device Inventory</h1>
          <p>31,740 device points from Matrix DB · Searchable by building, type, point address</p>
        </div>
    </div>''', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        dev_search = st.text_input("🔍  Search by building, type, point address, or description", key='dev_search')
    with col2:
        dev_types_list = ['All','SD','HD','PS','DD','WF','TS','Trans','Ext','Beam','Flood','Vesda','Hood','PRE','CO2','AES Panel','AES Zone']
        type_f = st.selectbox("Device Type", dev_types_list)
    with col3:
        bldg_names = db.get_device_buildings()
        bldg_f = st.selectbox("Building", ['All'] + bldg_names)

    @st.cache_data(ttl=60)
    def load_devices(search, type_f, bldg_f):
        return db.search_devices(search, type_f, bldg_f)

    df = load_devices(dev_search, type_f, bldg_f)
    st.write(f"**{len(df):,}** devices shown (max 2,000 per page)")
    st.dataframe(df, use_container_width=True, hide_index=True, height=600,
                column_config={
                    'Type': st.column_config.TextColumn(width='small'),
                    'Point': st.column_config.TextColumn(width='small'),
                })


# ══════════════════════════════════════════════════════════════════════════════
# EDIT BUILDING
# ══════════════════════════════════════════════════════════════════════════════
elif page == "✏️  Edit Building":
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_HEADER_B64}" style="height:52px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>Edit Building Info</h1>
          <p>Update panel details, device counts, network info, and upload building images</p>
        </div>
    </div>''', unsafe_allow_html=True)

    buildings_list = db.get_buildings()

    # Handle prefill from Buildings page
    if not buildings_list:
        st.warning('No buildings loaded yet. Please wait for data to seed.')
        st.stop()
    if 'edit_bldg_num' not in st.session_state:
        st.session_state['edit_bldg_num'] = buildings_list[0]['bldg_num']

    bldg_nums_e   = [b['bldg_num'] for b in buildings_list]
    bldg_labels_e = [f"{b['bldg_num']} — {b['name']}" for b in buildings_list]
    cur_e = st.session_state['edit_bldg_num']
    cur_idx_e = bldg_nums_e.index(cur_e) if cur_e in bldg_nums_e else 0

    chosen_e = st.selectbox("Select Building to Edit", bldg_labels_e, index=cur_idx_e, key='edit_bldg_select')
    sel_num_e = bldg_nums_e[bldg_labels_e.index(chosen_e)]
    st.session_state['edit_bldg_num'] = sel_num_e
    eb = db.get_building(sel_num_e)
    if not eb:
        st.error("Building not found"); st.stop()

    st.divider()

    # ── Building Image ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Building Image</div>', unsafe_allow_html=True)
    img_col, upload_col = st.columns([1, 1])
    with img_col:
        img_path = get_local_building_image(sel_num_e)
        img_b64, img_ext = db.get_building_image(sel_num_e)

        if img_path:
            st.image(img_path, use_container_width=True)
        elif img_b64:
            st.image(f"data:image/{img_ext};base64,{img_b64}", caption=eb['name'], use_container_width=True)
        else:
            st.info("No building image found")
    with upload_col:
        uploaded_img = st.file_uploader("Upload Building Image", type=['jpg','jpeg','png'],
                                         key=f'img_upload_{sel_num_e}',
                                         help="JPG or PNG, any size — will display on inspection reports")
        if uploaded_img:
            ext = uploaded_img.name.rsplit('.',1)[-1].lower()
            db.save_building_image(sel_num_e, uploaded_img.read(), ext)
            st.success(f"Image saved for {eb['name']}")
            st.rerun()
        if img_b64:
            if st.button("🗑 Remove Image", key=f'del_img_{sel_num_e}'):
                db.delete_building_image(sel_num_e)
                st.success("Image removed")
                st.rerun()

    st.divider()

    # ── Editable Fields ────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Building Information</div>', unsafe_allow_html=True)
    with st.form(key=f'edit_bldg_form_{sel_num_e}'):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            st.markdown("**Basic Info**")
            new_name   = st.text_input("Building Name",     value=eb.get('name',''))
            new_dist   = st.text_input("District",          value=eb.get('district',''))
            new_addr   = st.text_input("Street Address",    value=eb.get('address',''))
            new_city   = st.text_input("City",              value=eb.get('city','') or 'Salt Lake City')
            new_state  = st.text_input("State",             value=eb.get('state','') or 'UT')
            new_zip    = st.text_input("Zip",               value=str(eb.get('zip','') or ''))
            new_built  = st.number_input("Year Built",      value=int(eb.get('built') or 1900), min_value=1800, max_value=2030)
            new_sqft   = st.number_input("Square Footage",  value=int(eb.get('sq_ft') or 0), min_value=0)
            new_aux    = st.selectbox("Auxiliary",          ['No','Yes'], index=0 if str(eb.get('aux','')).lower()!='yes' else 1)
        with fc2:
            st.markdown("**Panel & Network**")
            panel_opts = ['E-3','E-3 VOICE','S-3','7100','7200','Simplex','Other']
            cur_panel  = eb.get('panel_type','E-3')
            panel_idx  = panel_opts.index(cur_panel) if cur_panel in panel_opts else len(panel_opts)-1
            new_panel  = st.selectbox("Panel Type",         panel_opts, index=panel_idx)
            new_yr_ins = st.number_input("Year Installed",  value=int(eb.get('year_installed') or 2000), min_value=1950, max_value=2030)
            new_gw     = st.selectbox("Has Gateway",        ['Yes','No'], index=0 if str(eb.get('gateway','')).lower()=='yes' else 1)
            new_gw_ip  = st.text_input("Gateway IP",        value=eb.get('gateway_ip',''))
            new_anx_ip = st.text_input("ANX IP",            value=eb.get('anx_ip',''))
            new_subnet = st.text_input("Subnet",            value=eb.get('subnet',''))
            new_vlan   = st.text_input("VLAN",              value=str(eb.get('vlan','') or ''))
            new_fp_name= st.text_input("FocalPoint Name",   value=eb.get('focalpoint_name',''))
            new_aim    = st.text_input("AIM Asset #",       value=eb.get('aim_asset',''))
            new_panel_loc = st.text_input("Panel Location", value=eb.get('panel_location',''))
        with fc3:
            st.markdown("**Device Counts**")
            new_smoke  = st.number_input("Smoke Detectors", value=int(eb.get('smoke') or 0), min_value=0)
            new_heat   = st.number_input("Heat Detectors",  value=int(eb.get('heat') or 0), min_value=0)
            new_pull   = st.number_input("Pull Stations",   value=int(eb.get('pull') or 0), min_value=0)
            new_duct   = st.number_input("Duct Detectors",  value=int(eb.get('duct') or 0), min_value=0)
            new_init   = st.number_input("Init Devices (Total)", value=int(eb.get('init_devices') or 0), min_value=0)
            new_notif  = st.number_input("Notif Devices (Total)", value=int(float(eb.get('notif_devices') or 0)), min_value=0)
            new_nodes  = st.number_input("Nodes",           value=int(eb.get('nodes') or 0), min_value=0)
            new_trans  = st.number_input("Transponders",    value=int(eb.get('transponders') or 0), min_value=0)
            new_ttt    = st.number_input("Time to Test (hrs)", value=int(eb.get('time_to_test') or 0), min_value=0)
            new_priority = st.selectbox("Replacement Priority (1-5)",
                [1,2,3,4,5], index=int(eb.get('replacement_priority') or 1)-1)
            new_insp_month = st.selectbox("Inspection Month", MONTHS_NO_ALL,
                index=MONTHS_NO_ALL.index(eb.get('inspection_month','January'))
                      if eb.get('inspection_month','') in MONTHS_NO_ALL else 0)

        submitted = st.form_submit_button("💾  Save Changes", type="primary", use_container_width=True)
        if submitted:
            new_age = datetime.now().year - int(new_yr_ins)
            db.update_building(sel_num_e, {
                'name': new_name, 'district': new_dist, 'address': new_addr,
                'city': new_city, 'state': new_state, 'zip': new_zip,
                'built': new_built, 'sq_ft': new_sqft, 'aux': new_aux,
                'panel_type': new_panel, 'year_installed': new_yr_ins, 'age': new_age,
                'gateway': new_gw, 'gateway_ip': new_gw_ip, 'anx_ip': new_anx_ip,
                'subnet': new_subnet, 'vlan': new_vlan,
                'focalpoint_name': new_fp_name, 'aim_asset': new_aim,
                'panel_location': new_panel_loc,
                'smoke': new_smoke, 'heat': new_heat, 'pull': new_pull, 'duct': new_duct,
                'init_devices': new_init, 'notif_devices': new_notif,
                'nodes': new_nodes, 'transponders': new_trans,
                'time_to_test': new_ttt, 'replacement_priority': new_priority,
                'inspection_month': new_insp_month,
            })
            st.success(f"✅ Building **{new_name}** updated successfully!")
            st.rerun()

    # Quick nav button
    if st.button("📋 Start Inspection for this Building", type="primary"):
        st.session_state['prefill_bldg'] = sel_num_e
        st.session_state['nav_target'] = '📋  New Inspection'
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PRINT REPORT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🖨️  Print Report":
    rdata = st.session_state.get('print_report_data')

    if not rdata:
        st.info("No report loaded. Open a saved report from **Inspection History** → 🖨️ Print Report, or fill out a New Inspection and click Preview & Print.")
        if st.button("← Go to Inspection History"):
            st.session_state['nav_target'] = '📁  Inspection History'
            st.rerun()
        st.stop()

    b      = rdata['bldg']
    result = rdata.get('result', 'PASS')
    pct    = rdata.get('pct', 0)
    defs   = rdata.get('defs', [])

    # Build HTML pieces as plain strings — no nested f-strings
    result_clean = result.split('—')[0].strip()
    result_bg    = '#dcfce7' if 'PASS' in result else ('#fee2e2' if 'FAIL' in result else '#fef9c3')
    result_color = '#166534' if 'PASS' in result else ('#991b1b' if 'FAIL' in result else '#854d0e')

    # AES table
    aes_vals = rdata.get('aes', {})
    aes_headers = ''.join(f'<th>{k}</th>' for k in aes_vals)
    aes_cells   = ''.join(
        '<td style="text-align:center"><span class="{}">{}</span></td>'.format(
            'badge-pass' if v=='PASS' else ('badge-fail' if v=='FAIL' else 'badge-partial'), v)
        for v in aes_vals.values())

    # Device testing table
    dev_tested = rdata.get('dev_tested', {})
    dev_rows = ''
    for code, label in [('PS','Pull Stations'),('SD','Smoke Detectors'),('HD','Heat Detectors'),
                        ('DD','Duct Detectors'),('WF','Waterflow'),('TS','Tamper Switches'),
                        ('NOTIF','Notification Devices'),('Trans','Transponders')]:
        dt  = dev_tested.get(code, {})
        tot = int(dt.get('total', 0) or 0)
        tst = int(dt.get('tested', 0) or 0)
        rem = max(0, tot - tst)
        stat = dt.get('status', '—')
        badge = 'badge-pass' if stat=='TESTED' else ('badge-fail' if stat=='NOT TESTED' else 'badge-partial')
        dev_rows += '<tr><td><code>{}</code></td><td>{}</td><td style="text-align:right">{}</td><td style="text-align:right">{}</td><td style="text-align:right">{}</td><td><span class="{}">{}</span></td></tr>'.format(
            code, label, tot or '—', tst or '—', rem if tot else '—', badge, stat)

    # FocalPoint device results
    dev_results = rdata.get('device_results', {})
    if dev_results:
        bldg_devs = db.get_devices_for_building(b.get('focalpoint_name',''), b.get('name',''))
        dev_lookup = {str(i): d for i, d in enumerate(bldg_devs)}
        fp_rows = []
        for idx in sorted(dev_results, key=lambda x: int(x) if x.isdigit() else 0):
            rv = dev_results[idx]
            if rv not in ('Pass','Fail','N/A'): continue
            d2 = dev_lookup.get(idx, {})
            bc = 'badge-pass' if rv=='Pass' else ('badge-fail' if rv=='Fail' else 'badge-partial')
            fp_rows.append('<tr><td><code>{}</code></td><td>{}</td><td>{}</td><td><span class="{}">{}</span></td></tr>'.format(
                d2.get('type','—'), d2.get('point','—'), d2.get('description','—'), bc, rv))
        pass_c = sum(1 for v in dev_results.values() if v=='Pass')
        fail_c = sum(1 for v in dev_results.values() if v=='Fail')
        na_c   = sum(1 for v in dev_results.values() if v=='N/A')
        if fp_rows:
            fp_html = ('<div style="margin-bottom:10px;font-size:12px">'
                '<span style="color:#166534;font-weight:700">{} Pass</span> &nbsp;·&nbsp; '
                '<span style="color:#991b1b;font-weight:700">{} Fail</span> &nbsp;·&nbsp; '
                '<span style="color:#888">{} N/A</span> &nbsp;·&nbsp; '
                '<span style="color:#555">{} of {} devices marked</span></div>'
                '<table class="rpt-table"><thead><tr><th>Type</th><th>Point</th><th>Description</th><th>Result</th></tr></thead>'
                '<tbody>{}</tbody></table>').format(pass_c, fail_c, na_c, len(fp_rows), len(bldg_devs), ''.join(fp_rows))
        else:
            fp_html = '<p style="color:#888;font-style:italic;font-size:12px">No individual device results recorded.</p>'
    else:
        fp_html = '<p style="color:#888;font-style:italic;font-size:12px">No individual device results recorded.</p>'

    # Deficiencies table
    if defs:
        def_html = ('<table class="rpt-table"><thead><tr>'
                    '<th>Device</th><th>Location/Point</th><th>Issue Found</th><th>Part #</th><th>Fixed?</th>'
                    '</tr></thead><tbody>')
        for d2 in defs:
            def_html += '<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(
                d2.get('device',''), d2.get('location',''), d2.get('issue',''),
                d2.get('part',''), d2.get('corrected',''))
        def_html += '</tbody></table>'
    else:
        def_html = '<p style="color:#888;font-style:italic;font-size:12px">No deficiencies recorded.</p>'

    # Building image
    bldg_img_html = ''
    img_b64, img_ext = db.get_building_image(b.get('bldg_num',''))
    if img_b64:
        bldg_img_html = '<img src="data:image/{};base64,{}" style="width:100%;max-height:200px;object-fit:cover;border-radius:6px;margin-top:10px">'.format(
            img_ext, img_b64)

    # Logo
    logo_html = '<img src="data:image/png;base64,{}" style="height:80px;object-fit:contain">'.format(LOGO_B64_PRINT if LOGO_B64_PRINT else LOGO_B64)

    # ── Print CSS ──────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    @media print {
        [data-testid="stSidebar"],[data-testid="stHeader"],
        [data-testid="stToolbar"],[data-testid="stBottom"],
        .stButton, footer, .no-print { display: none !important; }
        .block-container { padding: 0 !important; max-width: 100% !important; margin: 0 !important; }
        body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
        .print-page { padding: 0 !important; }
    }
    .print-page { font-family: Arial, sans-serif; max-width: 920px; margin: 0 auto; }
    .rpt-header { border-bottom: 3px solid #CC2929; padding: 16px 0 16px; margin-bottom: 20px;
                  display: flex; align-items: center; justify-content: space-between; gap: 16px; }
    .rpt-section { border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px 16px; margin-bottom: 14px; }
    .rpt-section-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;
                         color: #CC2929; border-bottom: 1px solid #e5e7eb; padding-bottom: 7px; margin-bottom: 11px; }
    .rpt-grid  { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .rpt-field { padding: 8px 10px; background: #f9f9f9; border-radius: 6px; border-left: 3px solid #CC2929; }
    .rpt-label { font-size: 10px; color: #888; text-transform: uppercase; font-weight: 600; }
    .rpt-val   { font-size: 13px; color: #111; font-weight: 600; margin-top: 2px; }
    .rpt-table { width: 100%; border-collapse: collapse; font-size: 12px; }
    .rpt-table th { background: #1a1a1a; color: white; padding: 7px 10px; text-align: left; }
    .rpt-table td { padding: 6px 10px; border-bottom: 1px solid #e5e7eb; }
    .rpt-table tr:nth-child(even) td { background: #f9f9f9; }
    .badge-pass    { background:#dcfce7; color:#166534; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:700; }
    .badge-fail    { background:#fee2e2; color:#991b1b; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:700; }
    .badge-partial { background:#fef9c3; color:#854d0e; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:700; }
    .result-badge  { font-size: 20px; font-weight: 900; padding: 10px 20px; border-radius: 8px; }
    .sig-line { border-bottom: 1px solid #333; height: 32px; margin-bottom: 4px; }
    </style>
    """, unsafe_allow_html=True)

    # ── Assemble report HTML ────────────────────────────────────────────────────
    addr_str = ', '.join(filter(None, [b.get('address',''), b.get('city',''), b.get('state','')]))

    html_parts = [
        '<div class="print-page">',

        # Header
        '<div class="rpt-header">',
        logo_html,
        '<div style="flex:1;padding-left:20px;border-left:1px solid #e5e5e5">',
        '<div style="font-size:20px;font-weight:800;color:#1a1a1a">Annual Fire Alarm Inspection Report</div>',
        '<div style="font-size:11px;color:#888;margin-top:4px">NFPA 72 (2016) &nbsp;·&nbsp; IFC 2018 &nbsp;·&nbsp; Utah Fire Code R7-10</div>',
        '</div>',
        '<div class="result-badge" style="background:{};color:{}">'.format(result_bg, result_color),
        result_clean,
        '</div></div>',

        # Building info
        '<div class="rpt-section">',
        '<div class="rpt-section-title">Building Information</div>',
        '<div style="display:grid;grid-template-columns:2fr 1fr;gap:16px">',
        '<div class="rpt-grid">',
        '<div class="rpt-field"><div class="rpt-label">Building Name</div><div class="rpt-val">{}</div></div>'.format(b.get('name','—')),
        '<div class="rpt-field"><div class="rpt-label">Building #</div><div class="rpt-val">{}</div></div>'.format(b.get('bldg_num','—')),
        '<div class="rpt-field"><div class="rpt-label">Address</div><div class="rpt-val">{}</div></div>'.format(addr_str or '—'),
        '<div class="rpt-field"><div class="rpt-label">District</div><div class="rpt-val">{}</div></div>'.format(b.get('district','—')),
        '<div class="rpt-field"><div class="rpt-label">Panel Type</div><div class="rpt-val">{}</div></div>'.format(b.get('panel_type','—')),
        '<div class="rpt-field"><div class="rpt-label">Year Installed</div><div class="rpt-val">{}</div></div>'.format(b.get('year_installed','—')),
        '<div class="rpt-field"><div class="rpt-label">Panel Location</div><div class="rpt-val">{}</div></div>'.format(b.get('panel_location','—')),
        '<div class="rpt-field"><div class="rpt-label">Gateway IP</div><div class="rpt-val">{}</div></div>'.format(b.get('gateway_ip','—')),
        '</div>',
        '<div>{}</div>'.format(bldg_img_html),
        '</div></div>',

        # Inspection details
        '<div class="rpt-section">',
        '<div class="rpt-section-title">Inspection Details</div>',
        '<div class="rpt-grid">',
        '<div class="rpt-field"><div class="rpt-label">Date</div><div class="rpt-val">{}</div></div>'.format(rdata.get('date','—')),
        '<div class="rpt-field"><div class="rpt-label">Work Order #</div><div class="rpt-val">{}</div></div>'.format(rdata.get('wo','—') or '—'),
        '<div class="rpt-field"><div class="rpt-label">Type</div><div class="rpt-val">{}</div></div>'.format(rdata.get('type','—')),
        '<div class="rpt-field"><div class="rpt-label">Inspector</div><div class="rpt-val">{}</div></div>'.format(rdata.get('inspector','—') or '—'),
        '<div class="rpt-field"><div class="rpt-label">AIM Asset #</div><div class="rpt-val">{}</div></div>'.format(b.get('aim_asset','—')),
        '<div class="rpt-field"><div class="rpt-label">FocalPoint Name</div><div class="rpt-val">{}</div></div>'.format(b.get('focalpoint_name','—')),
        '</div></div>',

        # AES
        '<div class="rpt-section">',
        '<div class="rpt-section-title">AES Radio Test</div>',
        '<table class="rpt-table"><thead><tr>{}</tr></thead><tbody><tr>{}</tr></tbody></table>'.format(aes_headers, aes_cells),
        '</div>',

        # Device testing
        '<div class="rpt-section">',
        '<div class="rpt-section-title">Device Testing Results &nbsp;<span style="font-weight:400;color:#888">({:.0f}% tested)</span></div>'.format(pct),
        '<table class="rpt-table"><thead><tr><th>Code</th><th>Device Type</th><th style="text-align:right">Total</th><th style="text-align:right">Tested</th><th style="text-align:right">Remaining</th><th>Status</th></tr></thead>',
        '<tbody>{}</tbody></table>'.format(dev_rows),
        '</div>',

        # FP device results
        '<div class="rpt-section">',
        '<div class="rpt-section-title">FocalPoint Device Results</div>',
        fp_html,
        '</div>',

        # Deficiencies
        '<div class="rpt-section">',
        '<div class="rpt-section-title">Deficiencies</div>',
        def_html,
        '</div>',

        # Notes
        '<div class="rpt-section">',
        '<div class="rpt-section-title">Notes &amp; Summary</div>',
        '<p style="font-size:12px;color:#444;line-height:1.6">{}</p>'.format(rdata.get('notes','') or 'No additional notes.'),
        '<p style="font-size:11px;color:#888;margin-top:10px;font-style:italic">The fire alarm system has been tested in accordance with NFPA 72 (2016), IFC 2018, and Utah Fire Code R7-10.</p>',
        '</div>',

        # Signatures
        '<div class="rpt-section">',
        '<div class="rpt-section-title">Signatures</div>',
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:32px;margin-top:12px">',
        '<div><div class="sig-line"></div><div style="font-size:11px;color:#888">Inspector Signature &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Date</div></div>',
        '<div><div class="sig-line"></div><div style="font-size:11px;color:#888">Print Name &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Certification #</div></div>',
        '</div></div>',

        '</div>',  # /print-page
    ]

    st.markdown('\n'.join(html_parts), unsafe_allow_html=True)

    st.divider()
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        st.markdown("""
        <button onclick="window.print()" style="
            background:#CC2929;color:white;border:none;padding:10px 20px;
            border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;width:100%;
            font-family:sans-serif">
            🖨️ Print / Save PDF
        </button>""", unsafe_allow_html=True)
    with c2:
        if st.button("← Back to History", use_container_width=True):
            st.session_state['nav_target'] = '📁  Inspection History'
            st.rerun()
    with c3:
        st.caption("💡 In print dialog: set **Margins → None**, enable **Background graphics** for best results.")