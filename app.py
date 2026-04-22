import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json, os, sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(__file__))
import db_supabase as db
import db_sprinkler as dbs
import db_master as dbm
from db_config import validate_db_config, get_db_mode

# ── Direct Supabase client for operations not in db modules ──────────────────
_raw_sb = None
def get_raw_supabase():
    """Get a raw Supabase client directly, bypassing db_supabase module."""
    global _raw_sb
    if _raw_sb: return _raw_sb
    try:
        from supabase import create_client
        url = os.environ.get('SUPABASE_URL', '')
        key = os.environ.get('SUPABASE_KEY', '')
        if not url:
            # Try to get from db_config or st.secrets
            try:
                url = st.secrets.get('SUPABASE_URL', '') or st.secrets.get('supabase_url', '')
                key = st.secrets.get('SUPABASE_KEY', '') or st.secrets.get('supabase_key', '')
            except: pass
        if not url:
            # Try from the db module
            if hasattr(db, 'get_supabase_client'):
                _raw_sb = db.get_supabase_client()
                return _raw_sb
            if hasattr(db, '_sb'):
                _raw_sb = db._sb
                return _raw_sb
            if hasattr(db, 'sb'):
                _raw_sb = db.sb
                return _raw_sb
        if url and key:
            _raw_sb = create_client(url, key)
            return _raw_sb
    except: pass
    return None
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
    page_title="🔥 UofU Fire Systems",
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


# ── HELPERS ──────────────────────────────────────────────────────────────────
def render_header(title, subtitle="University of Utah · Facilities Management"):
    """Render the standard page header with logo — call once per page."""
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
    </div>''', unsafe_allow_html=True)


def sort_buildings_universal(buildings):
    """Sort buildings by number (numeric first, then alpha)."""
    def _key(b):
        n = str(b.get('bldg_num', ''))
        try: return (0, int(float(n)))
        except: return (1, n)
    return sorted(buildings, key=_key)

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, use_container_width=True)
    else:
        st.markdown("**DEPARTMENT OF FIRE SYSTEMS**")
    st.markdown("""<div style="font-size:11px;font-weight:700;text-align:center;color:#aaa;line-height:1.4;padding:2px 4px">Solving Problems, You Didn't Know You Had<br>in Ways You Wouldn't Understand<br><span style="font-weight:400">Since 2014</span></div>""", unsafe_allow_html=True)
    st.divider()

    # ── Build sidebar with section headers as static text ─────────────────
    # Define sections: (header_text, [page_names])
    _NAV_SECTIONS = [
        (None, [
            "📊  Dashboard",
            "🏛️  Buildings",
            "🗺️  Campus Map",
            "➕  Add / Import Buildings",
        ]),
        ("🔥  FIRE ALARM", [
            "📅  Schedule",
            "📋  New Inspection",
            "📁  Inspection History",
            "🔍  Device Inventory",
            "➕  Add / Import FA Devices",
        ]),
        ("🚿  SPRINKLER", [
            "📅  SP Schedule",
            "📋  SP New Inspection",
            "📁  SP Inspection History",
            "🔧  SP Component Inventory",
            "➕  Add / Import SP Components",
        ]),
        ("🛠️  TOOLS", [
            "⚠️  Deficiency Tracker",
            "📈  Analytics",
            "📥  Export Reports",
        ]),
        ("🖨️  PRINT", [
            "🖨️  Print Report",
        ]),
    ]

    # Flat list of all navigable pages
    NAV_PAGES = []
    for _, pages in _NAV_SECTIONS:
        NAV_PAGES.extend(pages)
    NAV_OPTIONS = NAV_PAGES  # backward compat

    # Programmatic navigation
    if 'nav_target' in st.session_state:
        target = st.session_state.pop('nav_target')
        if target in NAV_PAGES:
            st.session_state['nav_page'] = target

    # Default
    if 'nav_page' not in st.session_state:
        st.session_state['nav_page'] = "📊  Dashboard"

    # Render each section
    for hdr, pages in _NAV_SECTIONS:
        if hdr:
            st.markdown(
                f'<p style="font-size:10px;font-weight:700;letter-spacing:0.08em;'
                f'color:#666;margin:12px 0 2px 0;padding-top:8px;'
                f'border-top:1px solid #333">{hdr}</p>',
                unsafe_allow_html=True)
        for p in pages:
            is_active = st.session_state.get('nav_page') == p
            if st.button(
                p,
                key=f"nav_{p}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state['nav_page'] = p
                st.rerun()

    page = st.session_state.get('nav_page', "📊  Dashboard")

    # Style nav buttons to look like a nav list
    st.markdown("""<style>
    /* Make sidebar nav buttons compact */
    [data-testid="stSidebar"] .stButton > button {
        padding: 4px 10px !important;
        font-size: 13px !important;
        text-align: left !important;
        justify-content: flex-start !important;
        border: none !important;
        border-radius: 6px !important;
        margin: 1px 0 !important;
        min-height: 32px !important;
        height: auto !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="secondary"] {
        background: transparent !important;
        color: #e0e0e0 !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
        background: rgba(204,41,41,0.15) !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: rgba(204,41,41,0.25) !important;
        color: #fff !important;
        font-weight: 600 !important;
    }
    </style>""", unsafe_allow_html=True)



st.caption(f"Database mode: {active_db_mode}")

# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED BUILDINGS
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏛️  Buildings":
    import db_master as dbm
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>Campus Buildings</h1>
          <p>Fire Alarm · Sprinkler · Combined View · {192} buildings</p>
        </div>
    </div>''', unsafe_allow_html=True)

    all_buildings = dbm.get_master_buildings()
    all_buildings = dbm.sort_buildings(all_buildings)

    if not all_buildings:
        st.warning("No buildings found. Run master_buildings seed SQL first.")
        st.stop()

    # ── Filters ───────────────────────────────────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns([3, 1, 1, 1])
    with fc1:
        mb_search = st.text_input("🔍 Search by name, number, district, panel…", key='mb_search')
    with fc2:
        dist_opts = ['All'] + sorted(set(b['district'] for b in all_buildings if b.get('district')))
        mb_dist = st.selectbox("District", dist_opts, key='mb_dist')
    with fc3:
        panel_opts = ['All'] + sorted(set(b['panel_type'] for b in all_buildings if b.get('panel_type')))
        mb_panel = st.selectbox("Panel Type", panel_opts, key='mb_panel')
    with fc4:
        mb_has_sp = st.selectbox("Sprinkler", ['All', 'Has Sprinkler', 'No Sprinkler'], key='mb_sp')

    # Apply filters
    filtered = all_buildings
    if mb_search:
        q = mb_search.lower()
        filtered = [b for b in filtered if
                    q in str(b.get('name','')).lower() or
                    q in str(b.get('bldg_num','')).lower() or
                    q in str(b.get('district','')).lower() or
                    q in str(b.get('panel_type','')).lower() or
                    q in str(b.get('focalpoint_name','')).lower()]
    if mb_dist != 'All':
        filtered = [b for b in filtered if b.get('district') == mb_dist]
    if mb_panel != 'All':
        filtered = [b for b in filtered if b.get('panel_type') == mb_panel]
    if mb_has_sp == 'Has Sprinkler':
        filtered = [b for b in filtered if int(b.get('total_sp_components') or 0) > 0]
    elif mb_has_sp == 'No Sprinkler':
        filtered = [b for b in filtered if int(b.get('total_sp_components') or 0) == 0]

    def _i(v):
        try: return int(float(v)) if v not in (None,'') else ''
        except: return v

    # ── Two-column layout: table + detail ─────────────────────────────────────
    tbl_col, det_col = st.columns([3, 2])

    with tbl_col:
        st.caption(f"**{len(filtered)}** buildings — click a row to view details")

        def _n(v):
            """Safe int for numeric columns — None becomes pd.NA not empty string"""
            try: return int(float(v)) if v not in (None, '', 'None') else pd.NA
            except: return pd.NA

        df_tbl = pd.DataFrame([{
            '#':          b['bldg_num'],
            'Building':   b.get('name',''),
            'District':   b.get('district',''),
            'Panel':      b.get('panel_type',''),
            'Insp Month': b.get('inspection_month',''),
            'Init Dev':   _n(b.get('init_devices')),
            'Notif Dev':  _n(b.get('notif_devices')),
            'Sprinklers': _n(b.get('total_sp_components')),
            'Age (Yrs)':  _n(b.get('age')),
        } for b in filtered])

        def _color_age(val):
            try:
                v = int(val)
                if v >= 20: return 'color:#991b1b;font-weight:bold'
                if v >= 15: return 'color:#c2410c;font-weight:bold'
                if v >= 10: return 'color:#854d0e'
            except: pass
            return ''

        try:
            styled = df_tbl.style.map(_color_age, subset=['Age (Yrs)'])
        except:
            styled = df_tbl.style

        bldg_labels_mb = [dbm.building_label(b) for b in filtered]
        sel = st.dataframe(styled, use_container_width=True, hide_index=True, height=620,
                           on_select="rerun", selection_mode="single-row", key="mb_table")
        sel_rows = sel.get("selection", {}).get("rows", []) if sel else []
        if sel_rows and sel_rows[0] < len(bldg_labels_mb):
            st.session_state['mb_detail_sel'] = bldg_labels_mb[sel_rows[0]]

    with det_col:
        default_idx = 0
        if st.session_state.get('mb_detail_sel') in bldg_labels_mb:
            default_idx = bldg_labels_mb.index(st.session_state['mb_detail_sel'])

        chosen = st.selectbox("Building", bldg_labels_mb, index=default_idx, key='mb_detail_sel')
        if chosen:
            sel_num = chosen.split(' — ')[0]
            b = dbm.get_master_building(sel_num)
            if b:
                # Image
                img_b64, img_ext = dbm.get_building_image(sel_num)
                img_path = get_local_building_image(sel_num)
                if img_path:
                    st.image(img_path, use_container_width=True)
                elif img_b64:
                    st.image(f"data:image/{img_ext};base64,{img_b64}", use_container_width=True)

                # Tabs
                t_info, t_fa, t_sp, t_hist, t_edit = st.tabs(
                    ["📋 Info", "🔥 Fire Alarm", "🚿 Sprinkler", "📁 History", "✏️ Edit"])

                with t_info:
                    for lbl, val in [
                        ('Address',    f"{b.get('address','')} {b.get('city','')} {b.get('state','')} {b.get('zip','')}"),
                        ('District',   b.get('district','')),
                        ('Sq Ft',      f"{int(b.get('sq_ft') or 0):,}"),
                        ('AIM Asset',  b.get('aim_asset','')),
                        ('DFCM ID',    b.get('dfcm_id','')),
                        ('FP Network', b.get('focalpoint_network','')),
                        ('Riser Folder', b.get('riser_folder','')),
                    ]:
                        if val and str(val).strip():
                            st.write(f"**{lbl}:** {val}")

                    st.divider()
                    ia1, ia2 = st.columns(2)
                    with ia1:
                        if st.button("📋 Start FA Inspection", key=f'mb_fa_insp_{sel_num}',
                                     use_container_width=True, type="primary"):
                            st.session_state['prefill_bldg'] = sel_num
                            st.session_state['nav_target'] = '📋  New Inspection'
                            st.rerun()
                    with ia2:
                        if st.button("🚿 Start SP Inspection", key=f'mb_sp_insp_{sel_num}',
                                     use_container_width=True):
                            st.session_state['nav_target'] = '📋  SP New Inspection'
                            st.rerun()

                with t_fa:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**System**")
                        for lbl, val in [
                            ('Panel Type',     b.get('panel_type','')),
                            ('Year Installed', b.get('year_installed','')),
                            ('System Age',     f"{b.get('age','—')} yrs"),
                            ('Insp Month',     b.get('inspection_month','')),
                            ('Panel Location', b.get('panel_location','')),
                            ('FocalPoint',     b.get('focalpoint_name','')),
                            ('Auxiliary',      b.get('aux','')),
                        ]:
                            if val and str(val).strip():
                                st.write(f"**{lbl}:** {val}")
                    with col2:
                        st.markdown("**Network**")
                        for lbl, val in [
                            ('Gateway IP',  b.get('gateway_ip','')),
                            ('ANX IP',      b.get('anx_ip','')),
                            ('Gateway',     b.get('gateway_addr','')),
                            ('Subnet',      b.get('subnet','')),
                            ('VLAN',        b.get('vlan','')),
                            ('Nodes',       _i(b.get('nodes'))),
                            ('Transponders',_i(b.get('transponders'))),
                        ]:
                            if val not in ('', None):
                                st.write(f"**{lbl}:** {val}")

                    st.divider()
                    st.markdown("**Device Counts**")
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        for lbl, key in [('Initiating (Total)', 'init_devices'),
                                         ('Smoke Detectors',    'smoke'),
                                         ('Heat Detectors',     'heat'),
                                         ('Pull Stations',      'pull'),
                                         ('Duct Detectors',     'duct')]:
                            v = _i(b.get(key))
                            if v not in ('', None, 0):
                                st.write(f"**{lbl}:** {v}")
                    with dc2:
                        for lbl, key in [('Notification (Total)', 'notif_devices'),
                                         ('Nodes',               'nodes'),
                                         ('Transponders',        'transponders')]:
                            v = _i(b.get(key))
                            if v not in ('', None, 0):
                                st.write(f"**{lbl}:** {v}")

                    # ── Device Map ────────────────────────────────────────────
                    st.divider()
                    st.markdown("**Device Map**")
                    import glob as _glob

                    _maps_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Maps")
                    _map_path = None

                    if os.path.isdir(_maps_dir):
                        # Try exact match first, then zero-padded variants
                        _bnum = str(sel_num)
                        _candidates = [
                            os.path.join(_maps_dir, f"{_bnum}.pdf"),
                            os.path.join(_maps_dir, f"{_bnum.zfill(3)}.pdf"),
                            os.path.join(_maps_dir, f"{_bnum.zfill(2)}.pdf"),
                        ]
                        # Also fuzzy: any pdf starting with the building number
                        _fuzzy = _glob.glob(os.path.join(_maps_dir, f"{_bnum}*.pdf")) +                                  _glob.glob(os.path.join(_maps_dir, f"{_bnum.zfill(3)}*.pdf"))
                        for _cp in _candidates + _fuzzy:
                            if os.path.exists(_cp):
                                _map_path = _cp
                                break

                    if _map_path:
                        _fname = os.path.basename(_map_path)
                        with open(_map_path, 'rb') as _f:
                            _pdf_bytes = _f.read()
                        st.download_button(
                            label=f"🗺️ Open Device Map — {_fname}",
                            data=_pdf_bytes,
                            file_name=_fname,
                            mime="application/pdf",
                            key=f"map_dl_{sel_num}",
                            use_container_width=True,
                            type="primary")
                        st.caption("Click to open — your browser will display the PDF")
                    else:
                        st.info("No device map on file for this building.")

                with t_sp:
                    sp_comps = dbm.get_sp_components(b)
                    total = _i(b.get('total_sp_components'))
                    riser_folder = b.get('riser_folder','')
                    if not sp_comps:
                        st.info("No sprinkler components on record for this building.")
                    else:
                        st.markdown(f"**Total Counted Components: {total}**")

                        # Check if any photos exist for this building
                        all_imgs = dbm.get_all_component_images(sel_num, riser_folder)
                        if all_imgs:
                            st.caption(f"📷 {len(all_imgs)} component photos on file — select a component to view")

                        st.divider()

                        # Component selector + image viewer
                        comp_list = sorted(sp_comps.keys())
                        sel_comp = st.selectbox("View Component Photo",
                                                ["— Select —"] + comp_list,
                                                key=f"sp_comp_sel_{sel_num}")

                        if sel_comp and sel_comp != "— Select —":
                            # Fuzzy image search — finds photos even with path mismatches
                            img_matches = dbm.get_component_images_fuzzy(sel_num, riser_folder, sel_comp)

                            if img_matches:
                                if len(img_matches) > 1:
                                    img_idx = st.selectbox(
                                        f"{len(img_matches)} photo(s) found — select location",
                                        range(len(img_matches)),
                                        format_func=lambda i: img_matches[i][1] or f"Photo {i+1}",
                                        key=f"sp_img_idx_{sel_num}_{sel_comp}")
                                else:
                                    img_idx = 0
                                p, loc = img_matches[img_idx]
                                st.image(p, caption=f"{sel_comp} — {loc}",
                                         use_container_width=True)
                            else:
                                st.info(f"No photo on file for {sel_comp}")

                        st.divider()
                        # Component count table in two columns
                        items = sorted(sp_comps.items(), key=lambda x: -x[1])
                        mid = (len(items) + 1) // 2
                        sp1, sp2 = st.columns(2)
                        with sp1:
                            for comp, cnt in items[:mid]:
                                st.write(f"**{comp}:** {cnt}")
                        with sp2:
                            for comp, cnt in items[mid:]:
                                st.write(f"**{comp}:** {cnt}")

                with t_hist:
                    import db_supabase as db
                    fa_hist = db.get_inspections(sel_num)
                    import db_sprinkler as dbs
                    sp_hist = dbs.get_sprinkler_inspections(sel_num)

                    if fa_hist:
                        st.markdown("**🔥 Fire Alarm Inspections**")
                        fa_df = pd.DataFrame([{
                            'Date':      h.get('inspection_date',''),
                            'Result':    h.get('result',''),
                            'Inspector': h.get('inspector_name',''),
                        } for h in fa_hist])
                        fa_sel = st.dataframe(fa_df, use_container_width=True, hide_index=True,
                                              on_select="rerun", selection_mode="single-row",
                                              key=f"mb_fa_hist_{sel_num}")
                        fa_rows = fa_sel.get("selection",{}).get("rows",[]) if fa_sel else []
                        if fa_rows:
                            h = fa_hist[fa_rows[0]]
                            st.session_state['last_print_type'] = 'fa'
                            st.session_state['print_report_data'] = {
                                'bldg': dbm.get_master_building(sel_num),
                                'date': h.get('inspection_date',''),
                                'wo': h.get('work_order',''),
                                'type': h.get('inspection_type',''),
                                'result': h.get('result',''),
                                'inspector': h.get('inspector_name',''),
                                'aes': {}, 'dev_tested': {},
                                'defs': h.get('deficiencies',[]) if isinstance(h.get('deficiencies'), list) else [],
                                'notes': h.get('notes',''), 'pct': h.get('pct_tested',0),
                                'device_results': {},
                            }
                            if st.button("🖨️ Print This Report", key=f"mb_fa_print_{sel_num}_{fa_rows[0]}"):
                                st.session_state.pop('sp_print_data', None)
                                st.session_state['nav_target'] = "🖨️  Print Report"
                                st.rerun()
                    else:
                        st.info("No fire alarm inspections saved.")

                    if sp_hist:
                        st.markdown("**🚿 Sprinkler Inspections**")
                        sp_df = pd.DataFrame([{
                            'Date':      h.get('inspection_date',''),
                            'Freq':      h.get('freq_type',''),
                            'Result':    h.get('overall_result',''),
                            'Inspector': h.get('inspector_name',''),
                        } for h in sp_hist])
                        sp_sel = st.dataframe(sp_df, use_container_width=True, hide_index=True,
                                              on_select="rerun", selection_mode="single-row",
                                              key=f"mb_sp_hist_{sel_num}")
                        sp_rows = sp_sel.get("selection",{}).get("rows",[]) if sp_sel else []
                        if sp_rows:
                            h = sp_hist[sp_rows[0]]
                            sp_items_hist = dbs.get_sprinkler_inspection_items(h['id'])
                            if sp_items_hist:
                                sp_items_df = pd.DataFrame([{
                                    'Component': i.get('component',''),
                                    'System':    i.get('system_type',''),
                                    'Status':    i.get('status',''),
                                    'Reading':   i.get('reading',''),
                                    'Comments':  i.get('comments',''),
                                } for i in sp_items_hist])
                                st.dataframe(sp_items_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("No sprinkler inspections saved.")

                with t_edit:
                    st.markdown("**Edit Building Info**")
                    with st.form(key=f'mb_edit_{sel_num}'):
                        e1, e2 = st.columns(2)
                        with e1:
                            new_name     = st.text_input("Building Name", value=b.get('name',''))
                            new_addr     = st.text_input("Address", value=b.get('address',''))
                            new_dist     = st.text_input("District", value=b.get('district',''))
                            new_panel    = st.text_input("Panel Type", value=b.get('panel_type',''))
                            new_month    = st.text_input("Inspection Month", value=b.get('inspection_month',''))
                            new_yr_ins   = st.number_input("Year Installed", value=int(b.get('year_installed') or 0), step=1)
                        with e2:
                            new_gw_ip    = st.text_input("Gateway IP", value=b.get('gateway_ip',''))
                            new_anx_ip   = st.text_input("ANX IP", value=b.get('anx_ip',''))
                            new_subnet   = st.text_input("Subnet", value=b.get('subnet',''))
                            new_vlan     = st.text_input("VLAN", value=b.get('vlan',''))
                            new_fp       = st.text_input("FocalPoint Name", value=b.get('focalpoint_name',''))
                            new_loc      = st.text_input("Panel Location", value=b.get('panel_location',''))

                        st.markdown("**Device Counts**")
                        d1, d2, d3 = st.columns(3)
                        with d1:
                            new_init  = st.number_input("Init Devices",   value=int(b.get('init_devices') or 0), min_value=0)
                            new_smoke = st.number_input("Smoke",          value=int(b.get('smoke') or 0), min_value=0)
                        with d2:
                            new_notif = st.number_input("Notif Devices",  value=int(b.get('notif_devices') or 0), min_value=0)
                            new_heat  = st.number_input("Heat",           value=int(b.get('heat') or 0), min_value=0)
                        with d3:
                            new_pull  = st.number_input("Pull Stations",  value=int(b.get('pull') or 0), min_value=0)
                            new_duct  = st.number_input("Duct",           value=int(b.get('duct') or 0), min_value=0)

                        # Image upload
                        st.markdown("**Building Image**")
                        up_img = st.file_uploader("Upload Image", type=['jpg','jpeg','png'],
                                                   key=f'mb_img_{sel_num}')

                        if st.form_submit_button("💾 Save Changes", type="primary"):
                            dbm.update_master_building(sel_num, {
                                'name': new_name, 'address': new_addr, 'district': new_dist,
                                'panel_type': new_panel, 'inspection_month': new_month,
                                'year_installed': new_yr_ins, 'gateway_ip': new_gw_ip,
                                'anx_ip': new_anx_ip, 'subnet': new_subnet, 'vlan': new_vlan,
                                'focalpoint_name': new_fp, 'panel_location': new_loc,
                                'init_devices': new_init, 'notif_devices': new_notif,
                                'smoke': new_smoke, 'heat': new_heat, 'pull': new_pull,
                                'duct': new_duct,
                            })
                            if up_img:
                                ext = up_img.name.rsplit('.',1)[-1].lower()
                                dbm.save_building_image(sel_num, up_img.read(), ext)
                            st.success(f"✅ {new_name} updated")
                            st.rerun()

                    if img_b64:
                        if st.button("🗑 Remove Image", key=f'mb_del_img_{sel_num}'):
                            dbm.delete_building_image(sel_num)
                            st.rerun()



# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊  Dashboard":
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>Fire Systems Dashboard</h1>
          <p>University of Utah · Facilities Management</p>
        </div>
    </div>''', unsafe_allow_html=True)

    stats = db.get_dashboard_stats()
    done = stats.get("complete", stats.get("inspections_complete", 0))
    scheduled = stats.get("scheduled", 0)
    done_pct = round(done / scheduled * 100) if scheduled else 0

    # Fire Alarm cards — Calendar Year to Date
    _cur_year = datetime.now().year
    st.markdown(f'<div style="font-size:11px;font-weight:700;letter-spacing:0.08em;color:#CC2929;text-transform:uppercase;margin-bottom:4px;border-bottom:2px solid #CC2929;padding-bottom:4px">🔥 FIRE ALARM SYSTEMS (NFPA 72) — {_cur_year} Year to Date</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""<div class="metric-card" style="--accent:#CC2929">
            <div class="label">Total Systems</div>
            <div class="value">{stats['total_systems']}</div>
            <div class="sub">Buildings monitored</div>
        </div>""", unsafe_allow_html=True)
        if st.button("→ Buildings", key='card_buildings', use_container_width=True):
            st.session_state['nav_target'] = '🏛️  Buildings'
            st.rerun()
    with c2:
        st.markdown(f"""<div class="metric-card" style="--accent:#166534">
            <div class="label">Inspections Complete</div>
            <div class="value" style="color:#166534">{stats['complete']}</div>
            <div class="sub">of {stats['scheduled']} scheduled · {done_pct}%</div>
        </div>""", unsafe_allow_html=True)
        if st.button("→ Schedule", key='card_complete', use_container_width=True):
            st.session_state['sched_status'] = 'Complete'
            st.session_state['nav_target'] = '📅  Schedule'
            st.rerun()
    with c3:
        color = '#991b1b' if stats['overdue'] > 0 else '#888'
        st.markdown(f"""<div class="metric-card" style="--accent:{color}">
            <div class="label">Overdue</div>
            <div class="value" style="color:{color}">{stats['overdue']}</div>
            <div class="sub">Past scheduled date</div>
        </div>""", unsafe_allow_html=True)
        if st.button("→ Schedule", key='card_overdue', use_container_width=True):
            st.session_state['sched_status'] = 'Overdue'
            st.session_state['nav_target'] = '📅  Schedule'
            st.rerun()
    with c4:
        st.markdown(f"""<div class="metric-card" style="--accent:#1e40af">
            <div class="label">Initiating Devices</div>
            <div class="value" style="color:#1e40af">{stats['init_devices']:,}</div>
            <div class="sub">Campus-wide total</div>
        </div>""", unsafe_allow_html=True)
        if st.button("→ Device Inventory", key='card_devices', use_container_width=True):
            st.session_state['nav_target'] = '🔍  Device Inventory'
            st.rerun()
    with c5:
        st.markdown(f"""<div class="metric-card" style="--accent:#854d0e">
            <div class="label">Reports Saved</div>
            <div class="value" style="color:#854d0e">{stats['reports_saved']}</div>
            <div class="sub">This cycle</div>
        </div>""", unsafe_allow_html=True)
        if st.button("→ Inspection History", key='card_reports', use_container_width=True):
            st.session_state['nav_target'] = '📁  Inspection History'
            st.rerun()

    # Sprinkler stats row — Fiscal Year (Jul–Jun)
    sp_stats = dbs.get_sprinkler_dashboard_stats()
    _fy_start_year = _cur_year if datetime.now().month >= 7 else _cur_year - 1
    _fy_label = f"FY{_fy_start_year + 1} (Jul {_fy_start_year} – Jun {_fy_start_year + 1})"
    st.markdown(f'<div class="section-title" style="margin-top:16px">Sprinkler Systems (NFPA 25) — {_fy_label}</div>', unsafe_allow_html=True)
    sp1, sp2, sp3, sp4, sp5 = st.columns(5)
    with sp1:
        st.markdown(f"""<div class="metric-card" style="--accent:#0369a1">
            <div class="label">Total Systems</div>
            <div class="value" style="color:#0369a1">{sp_stats['total_systems']}</div>
            <div class="sub">Buildings w/ sprinklers</div>
        </div>""", unsafe_allow_html=True)
        if st.button("→ Sprinkler", key='sp_card_systems', use_container_width=True):
            st.session_state['nav_target'] = '🚿  Sprinkler'
            st.rerun()
    with sp2:
        st.markdown(f"""<div class="metric-card" style="--accent:#166534">
            <div class="label">Complete</div>
            <div class="value" style="color:#166534">{sp_stats['complete']}</div>
            <div class="sub">This cycle</div>
        </div>""", unsafe_allow_html=True)
        if st.button("→ Schedule", key='sp_card_complete', use_container_width=True):
            st.session_state['nav_target'] = '🚿  Sprinkler'
            st.rerun()
    with sp3:
        sp_od_color = '#991b1b' if sp_stats['overdue'] > 0 else '#888'
        st.markdown(f"""<div class="metric-card" style="--accent:{sp_od_color}">
            <div class="label">Overdue</div>
            <div class="value" style="color:{sp_od_color}">{sp_stats['overdue']}</div>
            <div class="sub">Past scheduled date</div>
        </div>""", unsafe_allow_html=True)
    with sp4:
        st.markdown(f"""<div class="metric-card" style="--accent:#0891b2">
            <div class="label">Quarterly Due</div>
            <div class="value" style="color:#0891b2">{sp_stats['quarterly_due']}</div>
            <div class="sub">This month</div>
        </div>""", unsafe_allow_html=True)
    with sp5:
        st.markdown(f"""<div class="metric-card" style="--accent:#7c3aed">
            <div class="label">Annual Due</div>
            <div class="value" style="color:#7c3aed">{sp_stats['annual_due']}</div>
            <div class="sub">This month</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Dashboard Charts Row ──────────────────────────────────────────────
    dash_left, dash_right = st.columns([2, 1])
    with dash_left:
        st.markdown('<div class="section-title">Inspection Progress — Cumulative</div>', unsafe_allow_html=True)
        _mdata = {r['month']: r for r in stats.get('by_month', [])}
        _cum_done, _cum_total = [], []
        _rd, _rt = 0, 0
        for m in MONTHS_NO_ALL:
            md = _mdata.get(m, {})
            _rd += md.get('complete', 0)
            _rt += md.get('total', 0)
            _cum_done.append(_rd)
            _cum_total.append(_rt)
        _cfig = go.Figure()
        _cfig.add_trace(go.Scatter(x=MONTHS_NO_ALL, y=_cum_total, name='Target',
                                    mode='lines', line=dict(color='#CC2929', width=2, dash='dot')))
        _cfig.add_trace(go.Scatter(x=MONTHS_NO_ALL, y=_cum_done, name='Actual',
                                    mode='lines+markers', line=dict(color='#22c55e', width=3),
                                    fill='tozeroy', fillcolor='rgba(34,197,94,0.1)'))
        _cur = datetime.now().strftime('%B')
        if _cur in MONTHS_NO_ALL:
            _cfig.add_vline(x=MONTHS_NO_ALL.index(_cur), line_dash="dash",
                            line_color="#888", opacity=0.5,
                            annotation_text="Now", annotation_position="top right")
        _cfig.update_layout(height=260, margin=dict(l=0,r=0,t=10,b=0),
                            plot_bgcolor='white', paper_bgcolor='white',
                            legend=dict(orientation='h',y=-0.15),
                            yaxis=dict(showgrid=True, gridcolor='#f0f0f0'))
        st.plotly_chart(_cfig, use_container_width=True)

    with dash_right:
        # Mobile app link — prominent at top
        st.markdown(
            '<a href="https://uofufiresys.netlify.app" target="_blank" style="'
            'display:block;background:linear-gradient(135deg, #CC2929 0%, #9E1F1F 100%);'
            'border-radius:12px;padding:14px 16px;text-decoration:none;margin-bottom:10px;'
            'text-align:center;box-shadow:0 2px 8px rgba(158,31,31,0.3)">'
            '<div style="font-size:15px;font-weight:800;color:#fff">📱 Mobile Inspection App</div>'
            '<div style="font-size:11px;color:rgba(255,255,255,0.7);margin-top:3px">Open on your phone · Add to Home Screen</div>'
            '</a>', unsafe_allow_html=True)

        # Quick actions — 2x2 grid
        st.markdown('<div class="section-title">Quick Actions</div>', unsafe_allow_html=True)
        _qa1, _qa2 = st.columns(2)
        with _qa1:
            if st.button("🗺️ Map", use_container_width=True, key='dash_map'):
                st.session_state['nav_target'] = '🗺️  Campus Map'
                st.rerun()
            if st.button("📈 Analytics", use_container_width=True, key='dash_analytics'):
                st.session_state['nav_target'] = '📈  Analytics'
                st.rerun()
        with _qa2:
            if st.button("⚠️ Deficiencies", use_container_width=True, key='dash_def'):
                st.session_state['nav_target'] = '⚠️  Deficiency Tracker'
                st.rerun()
            if st.button("📥 Export", use_container_width=True, key='dash_export'):
                st.session_state['nav_target'] = '📥  Export Reports'
                st.rerun()

        # Quick deficiency count
        _all_insp = db.get_inspections()
        _def_count = 0
        for _insp in (_all_insp or []):
            _raw = _insp.get('deficiencies') or '[]'
            if isinstance(_raw, list): _def_count += len(_raw)
            else:
                try: _def_count += len(json.loads(_raw))
                except: pass
        _open_color = '#991b1b' if _def_count > 0 else '#166534'
        st.markdown(
            f'<div style="background:#f9f9f9;border-radius:8px;padding:12px;'
            f'border-left:4px solid {_open_color};margin-top:8px">'
            f'<div style="font-size:11px;color:#888;text-transform:uppercase;font-weight:600">Open Deficiencies</div>'
            f'<div style="font-size:28px;font-weight:800;color:{_open_color}">{_def_count}</div>'
            f'</div>', unsafe_allow_html=True)

    # ── Recent Activity — Last 7 Days ─────────────────────────────────────
    st.markdown('<div class="section-title" style="margin-top:16px">Recent Activity — Last 7 Days</div>', unsafe_allow_html=True)

    _7_days_ago = (date.today() - __import__('datetime').timedelta(days=7)).isoformat()

    # Collect all recent activity
    _activity = []

    # FA inspections
    _recent_fa = db.get_inspections()
    for insp in (_recent_fa or []):
        if (insp.get('inspection_date','') or '') >= _7_days_ago:
            is_mobile = 'mobile' in (insp.get('notes','') or '').lower() or \
                        insp.get('inspector_name','') == 'Mobile Inspector'
            _activity.append({
                'date': insp.get('inspection_date',''),
                'type': '🔥 FA Inspection',
                'building': f"#{insp.get('bldg_num','')} {insp.get('building_name','')}",
                'detail': insp.get('result',''),
                'inspector': insp.get('inspector_name',''),
                'source': '📱 Mobile' if is_mobile else '💻 Desktop',
                'source_color': '#3b82f6' if is_mobile else '#888',
                '_insp': insp,
            })

    # SP inspections
    _recent_sp = dbs.get_sprinkler_inspections()
    for insp in (_recent_sp or []):
        if (insp.get('inspection_date','') or '') >= _7_days_ago:
            is_mobile = 'mobile' in (insp.get('notes','') or '').lower() or \
                        insp.get('inspector_name','') == 'Mobile Inspector'
            _activity.append({
                'date': insp.get('inspection_date',''),
                'type': '🚿 SP Inspection',
                'building': f"#{insp.get('bldg_num','')} {insp.get('bldg_name','')}",
                'detail': f"{insp.get('freq_type','')} — {insp.get('overall_result','')}",
                'inspector': insp.get('inspector_name',''),
                'source': '📱 Mobile' if is_mobile else '💻 Desktop',
                'source_color': '#3b82f6' if is_mobile else '#888',
                '_insp': insp,
            })

    # Sort by date descending
    _activity.sort(key=lambda x: x['date'], reverse=True)

    if _activity:
        # Summary pills
        _act_total = len(_activity)
        _act_mobile = sum(1 for a in _activity if '📱' in a['source'])
        _act_fa = sum(1 for a in _activity if 'FA' in a['type'])
        _act_sp = sum(1 for a in _activity if 'SP' in a['type'])

        ac1, ac2, ac3, ac4 = st.columns(4)
        ac1.metric("Total Activity", _act_total)
        ac2.metric("📱 Mobile", _act_mobile)
        ac3.metric("🔥 Fire Alarm", _act_fa)
        ac4.metric("🚿 Sprinkler", _act_sp)

        # Clickable activity table
        _act_df = pd.DataFrame([{
            'Date':      a['date'],
            'Type':      a['type'],
            'Building':  a['building'],
            'Detail':    a['detail'],
            'Inspector': a['inspector'],
            'Source':     a['source'],
        } for a in _activity[:25]])

        _act_sel = st.dataframe(_act_df, use_container_width=True, hide_index=True,
                                height=min(400, len(_act_df)*38+40),
                                on_select="rerun", selection_mode="single-row",
                                key="dash_activity_tbl")
        _act_rows = _act_sel.get("selection",{}).get("rows",[]) if _act_sel else []

        if _act_rows and _act_rows[0] < len(_activity):
            _sel_act = _activity[_act_rows[0]]
            _sel_insp = _sel_act.get('_insp')

            if _sel_insp and 'FA' in _sel_act['type']:
                # Navigate to FA print report
                b_data = dbm.get_master_building(str(_sel_insp['bldg_num']))
                dev_tested_hist = {
                    code: {'total': _sel_insp.get(f'{code.lower()}_total',0),
                           'tested': _sel_insp.get(f'{code.lower()}_tested',0),
                           'status': 'TESTED'}
                    for code in ['PS','SD','HD','DD','WF','TS','NOTIF','Trans']
                }
                aes_hist = {k: _sel_insp.get(f'aes_{v}','—')
                    for k, v in [('Alarm','alarm'),('Supervisory','supv'),('Trouble','trouble'),
                                 ('Waterflow','wf'),('Tamper','tamper'),('Duct','duct'),('Fire Ext','ext')]}
                raw_defs = _sel_insp.get('deficiencies') or '[]'
                if isinstance(raw_defs, list): _defs = raw_defs
                else:
                    try: _defs = json.loads(raw_defs)
                    except: _defs = []

                _ac1, _ac2, _ac3 = st.columns([1, 1, 1])
                with _ac1:
                    if st.button("🖨️ Print Report", key=f"act_print_fa_{_sel_insp['id']}", type="primary",
                                 use_container_width=True):
                        st.session_state['last_print_type'] = 'fa'
                        st.session_state['print_report_data'] = {
                            'bldg': b_data or {'name': _sel_insp.get('building_name',''), 'bldg_num': _sel_insp.get('bldg_num',''),
                                               'district':'','address':'','panel_type':'','year_installed':'','panel_location':'',
                                               'aim_asset':'','gateway_ip':'','focalpoint_name':''},
                            'date': _sel_insp.get('inspection_date',''),
                            'wo': _sel_insp.get('work_order',''),
                            'type': _sel_insp.get('inspection_type',''),
                            'result': _sel_insp.get('result',''),
                            'inspector': _sel_insp.get('inspector_name',''),
                            'aes': aes_hist, 'dev_tested': dev_tested_hist,
                            'defs': _defs,
                            'notes': _sel_insp.get('notes',''),
                            'pct': _sel_insp.get('pct_tested', 0),
                            'device_results': {},
                        }
                        st.session_state.pop('sp_print_data', None)
                        st.session_state['nav_page'] = '🖨️  Print Report'
                        st.rerun()
                with _ac2:
                    if st.button("📁 View in History", key=f"act_hist_fa_{_sel_insp['id']}",
                                 use_container_width=True):
                        st.session_state['nav_page'] = '📁  Inspection History'
                        st.rerun()
                with _ac3:
                    if st.button("🏛️ View Building", key=f"act_bldg_fa_{_sel_insp.get('bldg_num','')}",
                                 use_container_width=True):
                        st.session_state['mb_detail_sel'] = f"{_sel_insp.get('bldg_num','')} — {_sel_insp.get('building_name','')}"
                        st.session_state['nav_page'] = '🏛️  Buildings'
                        st.rerun()

            elif _sel_insp and 'SP' in _sel_act['type']:
                # Navigate to SP print report
                _sp_items = dbs.get_sprinkler_inspection_items(_sel_insp['id'])

                _ac1, _ac2, _ac3 = st.columns([1, 1, 1])
                with _ac1:
                    if st.button("🖨️ Print Report", key=f"act_print_sp_{_sel_insp['id']}", type="primary",
                                 use_container_width=True):
                        st.session_state['last_print_type'] = 'sp'
                        st.session_state['sp_print_data'] = {
                            'bldg_num':   _sel_insp.get('bldg_num',''),
                            'bldg_name':  _sel_insp.get('bldg_name',''),
                            'freq_type':  _sel_insp.get('freq_type',''),
                            'date':       _sel_insp.get('inspection_date',''),
                            'inspector':  _sel_insp.get('inspector_name',''),
                            'result':     _sel_insp.get('overall_result',''),
                            'notes':      _sel_insp.get('notes',''),
                            'items':      _sp_items or [],
                            'insp_id':    _sel_insp['id'],
                        }
                        st.session_state.pop('print_report_data', None)
                        st.session_state['nav_page'] = '🖨️  Print Report'
                        st.rerun()
                with _ac2:
                    if st.button("📁 View in History", key=f"act_hist_sp_{_sel_insp['id']}",
                                 use_container_width=True):
                        st.session_state['nav_page'] = '📁  SP Inspection History'
                        st.rerun()
                with _ac3:
                    if st.button("🏛️ View Building", key=f"act_bldg_sp_{_sel_insp.get('bldg_num','')}",
                                 use_container_width=True):
                        st.session_state['mb_detail_sel'] = f"{_sel_insp.get('bldg_num','')} — {_sel_insp.get('bldg_name','')}"
                        st.session_state['nav_page'] = '🏛️  Buildings'
                        st.rerun()

        # Show mobile submissions specifically if any
        if _act_mobile > 0:
            with st.expander(f"📱 Mobile Submissions ({_act_mobile})", expanded=False):
                _mob_df = pd.DataFrame([{
                    'Date':      a['date'],
                    'Type':      a['type'],
                    'Building':  a['building'],
                    'Detail':    a['detail'],
                    'Inspector': a['inspector'],
                } for a in _activity if '📱' in a['source']])
                st.dataframe(_mob_df, use_container_width=True, hide_index=True)
    else:
        st.info("No inspection activity in the last 7 days.")

    # ── Edit Log — Mobile & Desktop Changes ──────────────────────────────
    st.markdown('<div class="section-title" style="margin-top:16px">📝 Edit Log — Recent Changes</div>', unsafe_allow_html=True)
    try:
        _sb_log = get_raw_supabase()
        if _sb_log:
            _log_res = _sb_log.table('edit_log').select('*').order('created_at', desc=True).limit(25).execute()
            _log_data = _log_res.data if _log_res and _log_res.data else []
            if _log_data:
                _log_df = pd.DataFrame([{
                    'Time':     l.get('created_at','')[:16].replace('T',' '),
                    'Source':   '📱' if l.get('source') == 'mobile' else '💻',
                    'Action':   l.get('action',''),
                    'Type':     l.get('entity_type','').replace('_',' ').title(),
                    'Building': f"#{l.get('bldg_num','')} {l.get('building_name','')}",
                    'Details':  l.get('details',''),
                    'By':       l.get('inspector_name',''),
                } for l in _log_data])

                _log_sel = st.dataframe(_log_df, use_container_width=True, hide_index=True,
                                         height=min(300, len(_log_df)*38+40),
                                         on_select="rerun", selection_mode="single-row",
                                         key="dash_edit_log_tbl")
                _log_rows = _log_sel.get("selection",{}).get("rows",[]) if _log_sel else []

                if _log_rows and _log_rows[0] < len(_log_data):
                    _sel_log = _log_data[_log_rows[0]]
                    _etype = _sel_log.get('entity_type','')
                    _eid = _sel_log.get('entity_id','')

                    _lc1, _lc2, _lc3 = st.columns(3)
                    with _lc1:
                        if 'fa_inspection' in _etype and _eid:
                            if st.button("📁 View FA Report", key=f"log_fa_{_eid}", use_container_width=True):
                                st.session_state['nav_page'] = '📁  Inspection History'
                                st.rerun()
                        elif 'sp_inspection' in _etype and _eid:
                            if st.button("📁 View SP Report", key=f"log_sp_{_eid}", use_container_width=True):
                                st.session_state['nav_page'] = '📁  SP Inspection History'
                                st.rerun()
                    with _lc2:
                        _log_bnum = _sel_log.get('bldg_num','')
                        if _log_bnum:
                            if st.button("🏛️ View Building", key=f"log_bldg_{_log_bnum}", use_container_width=True):
                                st.session_state['mb_detail_sel'] = f"{_log_bnum} — {_sel_log.get('building_name','')}"
                                st.session_state['nav_page'] = '🏛️  Buildings'
                                st.rerun()
                    with _lc3:
                        if _sel_log.get('field_changed'):
                            st.caption(f"Changed: **{_sel_log['field_changed']}**\n\n"
                                       f"Old: `{_sel_log.get('old_value','')}`\n\n"
                                       f"New: `{_sel_log.get('new_value','')}`")
            else:
                st.info("No edit log entries yet. Edits from the mobile app will appear here.")
        else:
            st.caption("Edit log requires Supabase connection.")
    except Exception as _le:
        st.caption(f"Edit log not available — run create_inspectors_and_log.sql first. ({_le})")

elif page == "📅  Schedule":
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>2026 Inspection Schedule</h1>
          <p>Click any row to update status · Changes save instantly to the database</p>
        </div>
    </div>''', unsafe_allow_html=True)


    # Monthly progress chart + upcoming
    _fa_stats = db.get_dashboard_stats()
    _chart_left, _chart_right = st.columns([2, 1])
    with _chart_left:
        st.markdown('<div class="section-title">Monthly Inspection Progress</div>', unsafe_allow_html=True)
        _mdata = {r['month']: r for r in _fa_stats.get('by_month', [])}
        _months = MONTHS_NO_ALL
        _done  = [_mdata.get(m, {}).get('complete', 0) for m in _months]
        _total = [_mdata.get(m, {}).get('total', 0) for m in _months]
        _rem   = [t - d for t, d in zip(_total, _done)]
        _cur   = datetime.now().strftime('%B')
        _cfig = go.Figure()
        _cfig.add_trace(go.Bar(name='Complete', x=_months, y=_done,
            marker_color=['#22c55e']*12, text=_done, textposition='inside',
            textfont=dict(color='white', size=10)))
        _cfig.add_trace(go.Bar(name='Remaining', x=_months, y=_rem,
            marker_color=['#fbbf24' if m == _cur else '#CC2929' for m in _months],
            text=_rem, textposition='inside', textfont=dict(color='white', size=10)))
        _cfig.update_layout(barmode='stack', height=260,
            margin=dict(l=0,r=0,t=10,b=0), legend=dict(orientation='h',y=-0.15),
            plot_bgcolor='white', paper_bgcolor='white',
            xaxis=dict(tickfont=dict(size=10)), yaxis=dict(showgrid=True, gridcolor='#f0f0f0'))
        _cc = st.plotly_chart(_cfig, use_container_width=True, on_select="rerun", key="sched_fa_chart")
        if _cc and _cc.get("selection",{}).get("points"):
            _cm = _cc["selection"]["points"][0].get("x")
            if _cm: st.session_state['sched_month'] = _cm; st.rerun()
    with _chart_right:
        st.markdown(f'<div class="section-title">Upcoming in {_cur}</div>', unsafe_allow_html=True)
        _upcoming = [s for s in db.get_schedule(_cur) if s['status'] != 'Complete'][:8]
        if _upcoming:
            _udf = pd.DataFrame([{'Building': s['building_name'], 'Status': s['status'],
                                   'Est Hrs': s.get('est_hours','—')} for s in _upcoming])
            st.dataframe(_udf, use_container_width=True, hide_index=True, height=220)
        else:
            st.info(f"No pending in {_cur}")

    # Pre-select month if navigated from dashboard chart click
    if 'schedule_month_filter' in st.session_state:
        _pre_month = st.session_state.pop('schedule_month_filter')
        if _pre_month in MONTHS:
            st.session_state['sched_month'] = _pre_month

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
# ═══════════════════════════════════════════════════════════════════════════════════════════
elif page == "📋  New Inspection":
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>New Fire Alarm Inspection</h1>
          <p>NFPA 72 · University of Utah · Facilities Management</p>
        </div>
    </div>''', unsafe_allow_html=True)

    buildings = dbm.get_master_buildings()
    buildings = dbm.sort_buildings(buildings)
    bldg_nums   = [b["bldg_num"] for b in buildings]
    bldg_labels = [f"{b['bldg_num']} — {b.get('name') or b.get('name_alarm','')}" for b in buildings]

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
    b = dbm.get_master_building(sel_num)

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

        _def_key = f'deficiencies_{sel_num}'
        if _def_key not in st.session_state:
            st.session_state[_def_key] = []

        # Auto-populate deficiencies from failed FP devices
        fp_results_key = f'fp_results_{sel_num}'
        fp_res_cur = st.session_state.get(fp_results_key, {})
        if fp_res_cur and fp_devices:
            existing_points = {d.get('location','') for d in st.session_state[_def_key]}
            for idx_str, result in fp_res_cur.items():
                if result == 'Fail':
                    try:
                        dev = fp_devices[int(idx_str)]
                        point = str(dev.get('point', idx_str))
                        if point not in existing_points:
                            dtype = str(dev.get('type', ''))
                            desc  = str(dev.get('description', ''))
                            st.session_state[_def_key].append({
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
                st.session_state[_def_key].append(
                    {'device': '', 'location': '', 'issue': '', 'part': '', 'corrected': 'No'})
        with col_clear:
            if st.button("🔄 Sync Failed Devices", help="Re-pull all Fail results from FocalPoint list"):
                existing_points = set()
                st.session_state[_def_key] = []
                for idx_str, result in fp_res_cur.items():
                    if result == 'Fail':
                        try:
                            dev = fp_devices[int(idx_str)]
                            point = str(dev.get('point', idx_str))
                            if point not in existing_points:
                                dtype = str(dev.get('type', ''))
                                desc  = str(dev.get('description', ''))
                                st.session_state[_def_key].append({
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

        for i, d in enumerate(st.session_state[_def_key]):
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
                        st.session_state[_def_key].pop(i)
                        st.rerun()

        if not st.session_state[_def_key]:
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
                insp_id = db.save_inspection(data, st.session_state[_def_key])
                # Save FocalPoint device results
                fp_results_key = f'fp_results_{sel_num}'
                fp_res = st.session_state.get(fp_results_key, {})
                if fp_res:
                    db.save_device_results(insp_id, fp_res)
                st.session_state[_def_key] = []
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
                st.session_state['last_print_type'] = 'fa'
                st.session_state['print_report_data'] = {
                    'bldg': b, 'date': str(insp_date), 'wo': work_order,
                    'type': insp_type, 'result': result, 'inspector': inspector,
                    'aes': aes_vals, 'dev_tested': dev_tested,
                    'defs': list(st.session_state.get(_def_key, [])),
                    'notes': notes, 'pct': pct,
                    'device_results': captured_fp,
                }
                st.session_state.pop('sp_print_data', None)
                st.session_state['nav_target'] = '🖨️  Print Report'
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# INSPECTION HISTORY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📁  Inspection History":
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>Fire Alarm Inspection History</h1>
          <p>Saved inspection reports · Click any row to view, print, or edit</p>
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
        raw_defs = insp.get('deficiencies') or '[]'
        if isinstance(raw_defs, list):
            defs = raw_defs
        else:
            try: defs = json.loads(raw_defs)
            except: defs = []

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
                    b_data = dbm.get_master_building(str(insp['bldg_num']))
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
                    st.session_state['last_print_type'] = 'fa'
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
                        'defs': (insp.get('deficiencies') if isinstance(insp.get('deficiencies'), list)
                                 else (json.loads(insp.get('deficiencies') or '[]') if isinstance(insp.get('deficiencies'), str) else [])),
                        'notes': insp.get('notes',''),
                        'pct': insp.get('pct_tested', 0),
                        'device_results': {k:v for k,v in db.get_device_results(insp['id']).items() if v != '—'},
                    }
                    st.session_state.pop('sp_print_data', None)
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
          <h1>Fire Alarm Device Inventory</h1>
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
        # Use master_buildings for full building list (FocalPoint names)
        _dev_bldgs = dbm.get_master_buildings()
        _dev_bldgs = dbm.sort_buildings(_dev_bldgs)
        _dev_fp_opts = [str(b.get('focalpoint_name') or '').strip()
                        for b in _dev_bldgs if str(b.get('focalpoint_name') or '').strip()]
        _dev_fp_map  = {str(b.get('focalpoint_name') or ''): b['bldg_num'] for b in _dev_bldgs}
        bldg_f = st.selectbox("Building", ['All'] + _dev_fp_opts,
                              format_func=lambda x: x if x == 'All' else
                              f"{_dev_fp_map.get(x, '')} — {x}")

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
# ═══════════════════════════════════════════════════════════════════════════════════════════
elif page == "📋  SP New Inspection":
    import db_sprinkler as dbs
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>Sprinkler System Inspection</h1>
          <p>NFPA 25 · University of Utah · Facilities Management</p>
        </div>
    </div>''', unsafe_allow_html=True)
    buildings = dbs.get_sprinkler_buildings()
    if not buildings:
        st.warning("No sprinkler buildings found. Run the Supabase seed SQL first.")
        st.stop()

    def _bsort(b):
        n = str(b.get('bldg_num',''))
        try: return (0, int(float(n)))
        except: return (1, n)

    buildings = sorted(buildings, key=_bsort)
    bldg_labels = [f"{b['bldg_num']} — {b['name']}" if b.get('name') else b['bldg_num']
                   for b in buildings]

    col_a, col_b, col_c = st.columns([2, 1, 1])
    with col_a:
        sel_label = st.selectbox("Building", bldg_labels, key='sp_bldg')
    with col_b:
        freq_opts = ['Quarterly','Semiannual','Annual','3-Year','5-Year']
        freq = st.selectbox("Inspection Frequency", freq_opts, key='sp_freq')
    with col_c:
        inspector = st.text_input("Inspector", key='sp_inspector',
                                  placeholder="Your name")

    sel_bnum = sel_label.split(' — ')[0]

    # ── 3rd Party Inspection ──────────────────────────────────────────────
    is_3rd_party = st.checkbox("🏢 This inspection was performed by a 3rd party contractor", key='sp_3rd_party')
    if is_3rd_party:
        st.markdown('<div style="background:#f0f9ff;border-left:4px solid #0369a1;padding:12px 16px;'
                    'border-radius:0 8px 8px 0;margin-bottom:12px">', unsafe_allow_html=True)
        tp1, tp2, tp3 = st.columns(3)
        with tp1:
            tp_company = st.text_input("Company Name *", key='sp_tp_company',
                                        placeholder="e.g. Western States Fire Protection")
        with tp2:
            tp_date = st.date_input("Date Performed", value=date.today(), key='sp_tp_date')
        with tp3:
            tp_contact = st.text_input("Contact / Tech Name", key='sp_tp_contact',
                                        placeholder="e.g. Mike Johnson")

        tp4, tp5 = st.columns(2)
        with tp4:
            tp_wo = st.text_input("Work Order / PO #", key='sp_tp_wo',
                                   placeholder="PO-2026-XXX")
        with tp5:
            tp_report = st.file_uploader("Upload 3rd Party Report (PDF/Image)",
                                          type=['pdf','jpg','jpeg','png'],
                                          key='sp_tp_report')
        if tp_report:
            st.success(f"📎 Attached: {tp_report.name} ({tp_report.size/1024:.0f} KB)")
        st.markdown('</div>', unsafe_allow_html=True)


    # Show print button if last inspection was just saved
    if 'sp_print_data' in st.session_state:
        _pd = st.session_state['sp_print_data']
        st.success(f"✅ Last saved: {_pd.get('bldg_name','')} — {_pd.get('freq_type','')} — {_pd.get('date','')}")
        pc1, pc2 = st.columns([1,1])
        with pc1:
            if st.button('🖨️ Print Last Saved Report', key='sp_print_last'):
                st.session_state.pop('print_report_data', None)
                st.session_state['nav_target'] = '🖨️  Print Report'
                st.rerun()
        with pc2:
            if st.button('✕ Dismiss', key='sp_print_dismiss'):
                del st.session_state['sp_print_data']
                st.rerun()
        st.divider()

    if st.button("🔍 Load Inspection Items", type="primary", key='sp_load'):
        with st.spinner("Pulling components from NFPA 25..."):
            items = dbs.get_inspection_items_for_building(sel_bnum, freq)
        if items:
            st.session_state['sp_items'] = items
            st.session_state['sp_bnum'] = sel_bnum
            st.session_state['sp_bname'] = sel_label.split(' — ',1)[-1] if ' — ' in sel_label else sel_label
            st.session_state['sp_freq_val'] = freq
            st.success(f"Loaded {len(items)} inspection items")
            st.rerun()
        else:
            st.warning("No NFPA 25 items matched for this building/frequency. "
                       "Check that sprinkler_inventory and nfpa25_standards are seeded.")

    # ── Inspection form ───────────────────────────────────────────────────
    if 'sp_items' in st.session_state and st.session_state.get('sp_bnum') == sel_bnum:
        items = st.session_state['sp_items']

        st.markdown(f"### {st.session_state.get('sp_bname','')} — {st.session_state.get('sp_freq_val','')} Inspection")
        st.caption(f"{len(items)} items required by NFPA 25")

        # Group by system type for easier navigation
        systems = {}
        for it in items:
            sys = it.get('system_type', 'Other')
            systems.setdefault(sys, []).append(it)

        # Summary bar
        results = [it.get('status','') for it in items]
        n_pass    = results.count('Pass')
        n_crit    = results.count('Critical')
        n_noncrit = results.count('Non Critical')
        n_imp     = results.count('Impairment')
        n_na      = results.count('N/A')
        n_done    = n_pass + n_crit + n_noncrit + n_imp + n_na
        st.markdown(
            f'<div style="background:#f9f9f9;border-radius:8px;padding:10px 16px;'
            f'border-left:3px solid #CC2929;margin-bottom:12px">'
            f'✅ <b>{n_pass}</b> Pass &nbsp;&nbsp;'
            f'🔴 <b>{n_crit}</b> Critical &nbsp;&nbsp;'
            f'🟡 <b>{n_noncrit}</b> Non Critical &nbsp;&nbsp;'
            f'⚠️ <b>{n_imp}</b> Impairment &nbsp;&nbsp;'
            f'— <b>{n_na}</b> N/A &nbsp;&nbsp;'
            f'{n_done}/{len(items)} complete'
            f'</div>', unsafe_allow_html=True)

        # Quick actions — global
        st.markdown("**Mark All Items:**")
        qa1, qa2, qa3, qa4 = st.columns(4)
        with qa1:
            if st.button("✅ All Pass", key='sp_all_pass'):
                for it in items: it['status'] = 'Pass'
                st.session_state['sp_items'] = items; st.rerun()
        with qa2:
            if st.button("🔴 All Critical", key='sp_all_crit'):
                for it in items: it['status'] = 'Critical'
                st.session_state['sp_items'] = items; st.rerun()
        with qa3:
            if st.button("— All N/A", key='sp_all_na'):
                for it in items: it['status'] = 'N/A'
                st.session_state['sp_items'] = items; st.rerun()
        with qa4:
            if st.button("🔄 Clear All", key='sp_clear'):
                for it in items: it['status'] = ''; it['reading'] = ''; it['comments'] = ''
                st.session_state['sp_items'] = items; st.rerun()

        st.divider()

        # Render each system as an expander
        for sys_name, sys_items in systems.items():
            sys_done  = sum(1 for it in sys_items if it.get('status'))
            sys_fails = sum(1 for it in sys_items if it.get('status') == 'Fail')
            label = f"**{sys_name}** — {sys_done}/{len(sys_items)} done"
            if sys_fails: label += f" · ⚠️ {sys_fails} FAIL"

            with st.expander(label, expanded=(sys_fails > 0)):
                # Per-system quick mark
                sm1, sm2, sm3, sm4 = st.columns(4)
                with sm1:
                    if st.button("✅ Pass All", key=f'sp_sys_pass_{sys_name}'):
                        for it in items:
                            if it.get('system_type') == sys_name: it['status'] = 'Pass'
                        st.session_state['sp_items'] = items; st.rerun()
                with sm2:
                    if st.button("🔴 Critical All", key=f'sp_sys_crit_{sys_name}'):
                        for it in items:
                            if it.get('system_type') == sys_name: it['status'] = 'Critical'
                        st.session_state['sp_items'] = items; st.rerun()
                with sm3:
                    if st.button("— N/A All", key=f'sp_sys_na_{sys_name}'):
                        for it in items:
                            if it.get('system_type') == sys_name: it['status'] = 'N/A'
                        st.session_state['sp_items'] = items; st.rerun()
                with sm4:
                    if st.button("🔄 Clear", key=f'sp_sys_clr_{sys_name}'):
                        for it in items:
                            if it.get('system_type') == sys_name:
                                it['status'] = ''; it['reading'] = ''; it['comments'] = ''
                        st.session_state['sp_items'] = items; st.rerun()
                for idx, it in enumerate(items):
                    if it.get('system_type') != sys_name: continue

                    # Header row
                    proc_color = {'Inspect':'#1e40af','Test':'#991b1b',
                                  'Maintenance':'#854d0e'}.get(it.get('procedure',''),'#555')
                    st.markdown(
                        f'<div style="background:#f8f8f8;border-radius:6px;padding:8px 12px;'
                        f'margin:6px 0;border-left:3px solid {proc_color}">'
                        f'<span style="font-weight:700">{it["component"]}</span>'
                        f'&nbsp;&nbsp;<span style="color:{proc_color};font-size:12px;'
                        f'font-weight:600">{it.get("procedure","")}</span>'
                        f'&nbsp;&nbsp;<span style="color:#888;font-size:11px">§{it.get("reference","")}</span>'
                        f'<br><span style="font-size:12px;color:#444">{it.get("criteria","")}</span>'
                        f'</div>', unsafe_allow_html=True)

                    r1, r2, r3 = st.columns([1, 1, 3])
                    with r1:
                        new_status = st.selectbox(
                            "Status", ['','Pass','Critical','Non Critical','N/A','Impairment','Not Tested'],
                            index=['','Pass','Critical','Non Critical','N/A','Impairment','Not Tested'].index(it.get('status',''))
                                  if it.get('status','') in ['','Pass','Critical','Non Critical','N/A','Impairment','Not Tested'] else 0,
                            key=f'sp_status_{idx}')
                        it['status'] = new_status
                    with r2:
                        it['reading'] = st.text_input("Reading", value=it.get('reading',''),
                                                       key=f'sp_read_{idx}',
                                                       placeholder="e.g. 141/125 psi")
                    with r3:
                        it['comments'] = st.text_input("Comments", value=it.get('comments',''),
                                                        key=f'sp_comm_{idx}')
                    # Flag fail
                    if it.get('status') in ('Critical','Impairment'):
                        st.error(f"⚠️ {it.get('status','').upper()} — {it['component']} at {it.get('floor','')} {it.get('room','')}")

        st.session_state['sp_items'] = items

        # ── Save section ──────────────────────────────────────────────────
        st.divider()
        st.markdown('<div class="section-title">Save Inspection</div>', unsafe_allow_html=True)
        sc1, sc2, sc3 = st.columns([1, 1, 2])
        with sc1:
            insp_date = st.date_input("Inspection Date", value=date.today(), key='sp_date')
        with sc2:
            n_crit_total  = sum(1 for it in items if it.get('status') in ('Critical','Impairment'))
            n_noncrit     = sum(1 for it in items if it.get('status') == 'Non Critical')
            n_done_total  = sum(1 for it in items if it.get('status') in ('Pass','Critical','Non Critical','N/A','Impairment'))
            crit_pct      = (n_crit_total / n_done_total * 100) if n_done_total else 0
            if crit_pct > 50:
                _auto_result = "FAIL — Critical Deficiencies"
                _result_opts = ["FAIL — Critical Deficiencies", "PARTIAL — Deficiencies Noted", "PASS"]
            elif n_crit_total > 0 or n_noncrit > 0:
                _auto_result = "PARTIAL — Deficiencies Noted"
                _result_opts = ["PARTIAL — Deficiencies Noted", "FAIL — Critical Deficiencies", "PASS"]
            else:
                _auto_result = "PASS"
                _result_opts = ["PASS", "PARTIAL — Deficiencies Noted", "FAIL — Critical Deficiencies"]
            overall = st.selectbox("Overall Result", _result_opts, key='sp_result')
            if n_done_total > 0:
                st.caption(f"{n_crit_total} Critical · {n_noncrit} Non Critical out of {n_done_total} items — auto-suggest: {_auto_result}")
        with sc3:
            sp_notes = st.text_area("Notes", height=68, key='sp_notes',
                                    placeholder="Overall condition, observations…")

        if st.button("💾 Save Inspection Report", type="primary", key='sp_save'):
            if not inspector and not is_3rd_party:
                st.error("Please enter inspector name before saving.")
            elif is_3rd_party and not tp_company:
                st.error("Please enter the 3rd party company name.")
            else:
                # Build inspector name — include 3rd party info if applicable
                if is_3rd_party:
                    _insp_name = f"{tp_contact or tp_company}" if tp_contact else tp_company
                    _tp_note = f"3rd Party: {tp_company}"
                    if tp_contact: _tp_note += f" ({tp_contact})"
                    if tp_wo: _tp_note += f" | WO: {tp_wo}"
                    _tp_note += f" | Performed: {tp_date}"
                    _notes_combined = f"{_tp_note}\n{sp_notes}" if sp_notes else _tp_note
                else:
                    _insp_name = inspector
                    _notes_combined = sp_notes

                header = {
                    'bldg_num':       sel_bnum,
                    'bldg_name':      st.session_state.get('sp_bname',''),
                    'freq_type':      st.session_state.get('sp_freq_val',''),
                    'inspection_date': str(tp_date if is_3rd_party else insp_date),
                    'inspector_name': _insp_name,
                    'overall_result': overall,
                    'notes':          _notes_combined,
                    'is_third_party': is_3rd_party,
                    'third_party_company': tp_company if is_3rd_party else None,
                    'third_party_wo': tp_wo if is_3rd_party else None,
                }
                save_items = [{k: it.get(k,'') for k in
                    ['component','system_type','floor','room','reference',
                     'frequency','procedure','criteria','status','reading','comments']}
                    for it in items]
                with st.spinner("Saving..."):
                    insp_id = dbs.save_sprinkler_inspection(header, save_items)
                if insp_id:
                    # Update schedule status — check ALL months, not just current
                    all_sched = dbs.get_sprinkler_schedule(
                        freq_type=st.session_state.get('sp_freq_val',''))
                    for s in (all_sched or []):
                        if str(s.get('bldg_num')) == sel_bnum and s.get('status') != 'Complete':
                            _insp_dt = str(tp_date if is_3rd_party else insp_date)
                            dbs.update_sprinkler_schedule_status(
                                s['id'], 'Complete', _insp_dt)

                    # Save 3rd party report file if uploaded
                    if is_3rd_party and tp_report:
                        try:
                            _rpt_dir = os.path.join(
                                os.path.dirname(os.path.abspath(__file__)),
                                "reports", "sprinkler", sel_bnum)
                            os.makedirs(_rpt_dir, exist_ok=True)
                            _rpt_ext = tp_report.name.rsplit('.',1)[-1].lower()
                            _rpt_name = f"SP_{sel_bnum}_{tp_company.replace(' ','_')}_{tp_date}.{_rpt_ext}"
                            with open(os.path.join(_rpt_dir, _rpt_name), 'wb') as _rf:
                                _rf.write(tp_report.read())
                            st.info(f"📎 Report saved: {_rpt_name}")
                        except Exception as _e:
                            st.warning(f"Report file couldn't be saved locally: {_e}")
                    st.success(f"✅ Inspection saved (ID #{insp_id})")
                    # Store for print
                    st.session_state['last_print_type'] = 'sp'
                    st.session_state['sp_print_data'] = {
                        'bldg_num':   sel_bnum,
                        'bldg_name':  st.session_state.get('sp_bname',''),
                        'freq_type':  st.session_state.get('sp_freq_val',''),
                        'date':       str(tp_date if is_3rd_party else insp_date),
                        'inspector':  _insp_name,
                        'result':     overall,
                        'notes':      _notes_combined,
                        'items':      save_items,
                        'insp_id':    insp_id,
                        'is_third_party': is_3rd_party,
                        'third_party_company': tp_company if is_3rd_party else None,
                    }
                    del st.session_state['sp_items']
                    st.rerun()
                else:
                    st.error("Save failed — check Supabase connection.")


elif page == "📅  SP Schedule":
    import db_sprinkler as dbs
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>Sprinkler Inspection Schedule</h1>
          <p>NFPA 25 · University of Utah · Facilities Management</p>
        </div>
    </div>''', unsafe_allow_html=True)

    # SP Monthly progress chart + upcoming
    _sp_stats = dbs.get_sprinkler_dashboard_stats()
    _sp_left, _sp_right = st.columns([2, 1])
    with _sp_left:
        st.markdown('<div class="section-title">Sprinkler Monthly Progress</div>', unsafe_allow_html=True)
        _spmdata = {r['month']: r for r in _sp_stats.get('by_month', [])}
        _spmonths = MONTHS_NO_ALL
        _spdone  = [_spmdata.get(m, {}).get('complete', 0) for m in _spmonths]
        _sptotal = [_spmdata.get(m, {}).get('total', 0) for m in _spmonths]
        _sprem   = [t - d for t, d in zip(_sptotal, _spdone)]
        _spcur   = datetime.now().strftime('%B')
        _spfig = go.Figure()
        _spfig.add_trace(go.Bar(name='Complete', x=_spmonths, y=_spdone,
            marker_color=['#22c55e']*12, text=_spdone, textposition='inside',
            textfont=dict(color='white', size=10)))
        _spfig.add_trace(go.Bar(name='Remaining', x=_spmonths, y=_sprem,
            marker_color=['#0891b2' if m == _spcur else '#1e40af' for m in _spmonths],
            text=_sprem, textposition='inside', textfont=dict(color='white', size=10)))
        _spfig.update_layout(barmode='stack', height=260,
            margin=dict(l=0,r=0,t=10,b=0), legend=dict(orientation='h',y=-0.15),
            plot_bgcolor='white', paper_bgcolor='white',
            xaxis=dict(tickfont=dict(size=10)), yaxis=dict(showgrid=True, gridcolor='#f0f0f0'))
        _spcc = st.plotly_chart(_spfig, use_container_width=True, on_select="rerun", key="sched_sp_chart")
        if _spcc and _spcc.get("selection",{}).get("points"):
            _spcm = _spcc["selection"]["points"][0].get("x")
            if _spcm: st.session_state['sp_sched_month'] = _spcm; st.rerun()
    with _sp_right:
        st.markdown(f'<div class="section-title">Upcoming in {_spcur}</div>', unsafe_allow_html=True)
        _sp_up = [s for s in dbs.get_sprinkler_schedule(month=_spcur) if s.get('status') != 'Complete'][:8]
        if _sp_up:
            _spudf = pd.DataFrame([{'Bldg': s['bldg_num'], 'Type': s.get('freq_type',''),
                                     'Status': s.get('status','')} for s in _sp_up])
            st.dataframe(_spudf, use_container_width=True, hide_index=True, height=220)
        else:
            st.info(f"No pending in {_spcur}")

    MONTHS = ['All','January','February','March','April','May','June',
              'July','August','September','October','November','December']
    sc1, sc2, sc3 = st.columns([1, 1, 2])
    with sc1:
        sp_month = st.selectbox("Month", MONTHS, key='sp_sched_month')
    with sc2:
        sp_ft = st.selectbox("Frequency", ['All','Annual','Quarterly','5-Year'], key='sp_sched_freq')
    with sc3:
        sp_search = st.text_input("Search building", placeholder="Name or number…", key='sp_sched_search')

    rows = dbs.get_sprinkler_schedule(
        month=sp_month if sp_month != 'All' else None,
        freq_type=sp_ft if sp_ft != 'All' else None)

    # Join building names
    bldg_names = {b['bldg_num']: b.get('name','') for b in dbs.get_sprinkler_buildings()}
    for r in rows:
        r['building_name'] = bldg_names.get(str(r['bldg_num']), '')

    if sp_search:
        q = sp_search.lower()
        rows = [r for r in rows if q in str(r.get('bldg_num','')).lower()
                or q in r.get('building_name','').lower()]

    complete = sum(1 for r in rows if r.get('status') == 'Complete')
    overdue  = sum(1 for r in rows if r.get('status') == 'Overdue')
    st.write(f"**{len(rows)}** entries · ✅ {complete} complete · 🔴 {overdue} overdue")

    for r in rows:
        badge_color = {'Complete':'#166534','Overdue':'#991b1b',
                       'Pending':'#854d0e','In Progress':'#1e40af'}.get(r.get('status',''),'#555')
        with st.expander(
            f"**{r['bldg_num']}** {r.get('building_name','')} · "
            f"{r.get('freq_type','')} · {r.get('month','')} · "
            f"[{r.get('status','')}]"):
            ec1, ec2, ec3 = st.columns([1, 1, 1])
            with ec1:
                new_stat = st.selectbox("Status",
                    ['Pending','In Progress','Complete','Overdue','Construction'],
                    index=['Pending','In Progress','Complete','Overdue','Construction'].index(
                        r['status'] if r.get('status') in
                        ['Pending','In Progress','Complete','Overdue','Construction'] else 'Pending'),
                    key=f"sp_sstat_{r['id']}")
            with ec2:
                done_date = st.date_input("Date Completed", value=None, key=f"sp_sdate_{r['id']}")
            with ec3:
                sp_snotes = st.text_input("Notes", value=r.get('notes',''), key=f"sp_snotes_{r['id']}")
            if st.button("💾 Save", key=f"sp_ssave_{r['id']}", type="primary"):
                dbs.update_sprinkler_schedule_status(
                    r['id'], new_stat,
                    done_date.isoformat() if done_date else None,
                    sp_snotes)
                st.success("Saved"); st.rerun()
            if st.button("📋 Start Inspection", key=f"sp_sinsp_{r['id']}"):
                st.session_state['sp_bldg'] = f"{r['bldg_num']} — {r.get('building_name','')}"
                st.session_state['sp_freq_sel'] = r.get('freq_type','Annual')
                st.rerun()


elif page == "📁  SP Inspection History":
    import db_sprinkler as dbs
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>Sprinkler Inspection History</h1>
          <p>NFPA 25 · University of Utah · Facilities Management</p>
        </div>
    </div>''', unsafe_allow_html=True)
    _sp_bldgs = dbs.get_sprinkler_buildings()
    def _sp_bsort(b):
        n = str(b.get('bldg_num',''))
        try: return (0, int(float(n)))
        except: return (1, n)
    _sp_bldgs = sorted(_sp_bldgs, key=_sp_bsort)
    bldg_labels = [f"{b['bldg_num']} — {b['name']}" if b.get('name') else b['bldg_num'] for b in _sp_bldgs]
    freq_opts = ['Quarterly','Semiannual','Annual','3-Year','5-Year']
    hb1, hb2 = st.columns([2, 1])
    with hb1:
        hist_bldg = st.selectbox("Filter by Building", ['All'] + bldg_labels, key='sp_hist_bldg')
    with hb2:
        hist_freq = st.selectbox("Frequency", ['All'] + freq_opts, key='sp_hist_freq')

    hist_bnum = hist_bldg.split(' — ')[0] if hist_bldg != 'All' else None
    inspections = dbs.get_sprinkler_inspections(hist_bnum)
    if hist_freq != 'All':
        inspections = [i for i in inspections if i.get('freq_type') == hist_freq]

    if not inspections:
        st.info("No sprinkler inspection records saved yet.")
    else:
        hist_df = pd.DataFrame([{
            'Date':      i.get('inspection_date',''),
            'Building':  f"{i.get('bldg_num','')} {i.get('bldg_name','')}",
            'Frequency': i.get('freq_type',''),
            'Result':    i.get('overall_result',''),
            'Inspector': i.get('inspector_name',''),
        } for i in inspections])
        selected_hist = st.dataframe(hist_df, use_container_width=True,
                                      hide_index=True, on_select="rerun",
                                      selection_mode="single-row", key="sp_hist_tbl")
        sel_hist_rows = selected_hist.get("selection",{}).get("rows",[]) if selected_hist else []
        if sel_hist_rows:
            insp = inspections[sel_hist_rows[0]]
            st.divider()
            st.markdown(f"### {insp.get('bldg_name','')} — {insp.get('freq_type','')} — {insp.get('inspection_date','')}")
            st.write(f"**Inspector:** {insp.get('inspector_name','')} &nbsp;&nbsp; **Result:** {insp.get('overall_result','')}")
            if insp.get('notes'): st.write(f"**Notes:** {insp['notes']}")
            items = dbs.get_sprinkler_inspection_items(insp['id'])
            if items:
                items_df = pd.DataFrame([{
                    'Component':   it.get('component',''),
                    'System':      it.get('system_type',''),
                    'Floor/Room':  f"{it.get('floor','')} {it.get('room','')}".strip(),
                    'Procedure':   it.get('procedure',''),
                    'Status':      it.get('status',''),
                    'Reading':     it.get('reading',''),
                    'Comments':    it.get('comments',''),
                } for it in items])
                st.dataframe(items_df, use_container_width=True, hide_index=True, height=400)
                fails = [it for it in items if it.get('status') in ('Critical','Non Critical','Impairment')]
                if fails:
                    st.error(f"⚠️ {len(fails)} deficiencies found:")
                    for f in fails:
                        st.write(f"• **{f['component']}** ({f.get('floor','')} {f.get('room','')}) — {f.get('comments','')}")

            # ── Edit Inspection ───────────────────────────────────────────
            with st.expander("✏️ Edit This Inspection", expanded=False):
                _ed1, _ed2, _ed3 = st.columns(3)
                with _ed1:
                    _ed_date = st.date_input("Inspection Date",
                        value=datetime.strptime(insp['inspection_date'], '%Y-%m-%d').date()
                              if insp.get('inspection_date') else date.today(),
                        key=f"sp_ed_date_{insp['id']}")
                with _ed2:
                    _result_opts = ['PASS', 'PARTIAL — Deficiencies Noted', 'FAIL — Critical Deficiencies']
                    _cur_result = insp.get('overall_result','PASS')
                    _ed_result = st.selectbox("Result", _result_opts,
                        index=_result_opts.index(_cur_result) if _cur_result in _result_opts else 0,
                        key=f"sp_ed_result_{insp['id']}")
                with _ed3:
                    _ed_inspector = st.text_input("Inspector",
                        value=insp.get('inspector_name',''),
                        key=f"sp_ed_insp_{insp['id']}")

                _ed4, _ed5 = st.columns(2)
                with _ed4:
                    _freq_opts = ['Quarterly','Semiannual','Annual','3-Year','5-Year']
                    _cur_freq = insp.get('freq_type','Quarterly')
                    _ed_freq = st.selectbox("Frequency", _freq_opts,
                        index=_freq_opts.index(_cur_freq) if _cur_freq in _freq_opts else 0,
                        key=f"sp_ed_freq_{insp['id']}")
                with _ed5:
                    _ed_bname = st.text_input("Building Name",
                        value=insp.get('bldg_name',''),
                        key=f"sp_ed_bname_{insp['id']}")

                _ed_notes = st.text_area("Notes", value=insp.get('notes',''),
                    key=f"sp_ed_notes_{insp['id']}", height=80)

                if st.button("💾 Save Changes", key=f"sp_ed_save_{insp['id']}", type="primary"):
                    try:
                        _sb_edit = get_raw_supabase()
                        if _sb_edit:
                            _sb_edit.table('sprinkler_inspections').update({
                                'inspection_date': str(_ed_date),
                                'overall_result': _ed_result,
                                'inspector_name': _ed_inspector,
                                'freq_type': _ed_freq,
                                'bldg_name': _ed_bname,
                                'notes': _ed_notes,
                            }).eq('id', insp['id']).execute()
                            st.success("✅ Updated")
                            st.rerun()
                        else:
                            st.error("Could not connect to Supabase")
                    except Exception as _ue:
                        st.error(f"Update failed: {_ue}")

            # ── Print / Delete buttons ────────────────────────────────────
            _sph1, _sph2 = st.columns([1, 1])
            with _sph1:
                if st.button("🖨️ Print This Report", key=f"sp_hist_print_{insp['id']}", type="primary",
                             use_container_width=True):
                    st.session_state['last_print_type'] = 'sp'
                    st.session_state['sp_print_data'] = {
                    'bldg_num':   insp.get('bldg_num',''),
                    'bldg_name':  insp.get('bldg_name',''),
                    'freq_type':  insp.get('freq_type',''),
                    'date':       insp.get('inspection_date',''),
                    'inspector':  insp.get('inspector_name',''),
                    'result':     insp.get('overall_result',''),
                    'notes':      insp.get('notes',''),
                    'items':      items if items else [],
                    'insp_id':    insp['id'],
                    }
                    st.session_state.pop('print_report_data', None)
                    st.session_state['nav_target'] = '🖨️  Print Report'
                    st.rerun()
            with _sph2:
                if st.button("🗑 Delete", key=f"sp_hist_del_{insp['id']}",
                             use_container_width=True):
                    try:
                        _sb_del = get_raw_supabase()
                        if _sb_del:
                            # Delete items first, then inspection
                            _sb_del.table('sprinkler_inspection_items').delete().eq('inspection_id', insp['id']).execute()
                            _sb_del.table('sprinkler_inspections').delete().eq('id', insp['id']).execute()
                            # Also delete any photos
                            try:
                                _sb_del.table('inspection_photos').delete().eq('inspection_type', 'sp').eq('inspection_id', insp['id']).execute()
                            except: pass
                            st.success("Deleted")
                            st.rerun()
                        elif hasattr(dbs, 'delete_sprinkler_inspection'):
                            dbs.delete_sprinkler_inspection(insp['id'])
                            st.success("Deleted")
                            st.rerun()
                        else:
                            st.error("Could not connect to Supabase for delete. Check db_config.")
                    except Exception as _de:
                        st.error(f"Delete failed: {_de}")



elif page == "🔧  SP Component Inventory":
    import db_sprinkler as dbs
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>Sprinkler Component Inventory</h1>
          <p>NFPA 25 · Search and browse all riser components by building, floor, system</p>
        </div>
    </div>''', unsafe_allow_html=True)

    @st.fragment
    def _inventory_tab():
        st.markdown('<div class="section-title">Search Sprinkler Components</div>', unsafe_allow_html=True)

        if 'sp_inv_df' not in st.session_state:
            with st.spinner("Loading inventory (one-time)..."):
                raw = dbs.get_full_inventory()
            if raw:
                st.session_state['sp_inv_df'] = pd.DataFrame(raw)
            else:
                st.warning("No inventory data. Run seed SQL first.")
                return

        df_all = st.session_state['sp_inv_df']
        bldg_map = {b['bldg_num']: b.get('name','') for b in dbs.get_sprinkler_buildings()}

        def _label(n):
            name = bldg_map.get(str(n),'')
            return f"{n} — {name}" if name else str(n)

        all_bldgs = sorted(df_all['bldg_num'].dropna().unique().tolist(),
                           key=lambda x: (0,int(float(x))) if str(x).replace('.','').isdigit() else (1,str(x)))
        st.caption(f"{len(df_all):,} total components across {len(all_bldgs)} buildings")

        # Row 1: search + building (building filters everything below)
        r1c1, r1c2, r1c3 = st.columns([2, 2, 1])
        with r1c1:
            inv_search = st.text_input("🔍 Free-text search", placeholder="Any field…", key='inv_search')
        with r1c2:
            inv_bldg = st.selectbox("Building", ['All'] + [_label(n) for n in all_bldgs], key='inv_bldg')
        with r1c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔄 Reload", key='inv_reload', use_container_width=True,
                         help="Refresh from database"):
                del st.session_state['sp_inv_df']
                st.rerun()

        # Apply building filter first so floor/system/component lists are scoped
        inv_bnum = inv_bldg.split(' — ')[0] if inv_bldg != 'All' else 'All'
        df_bldg = df_all[df_all['bldg_num'].astype(str) == str(inv_bnum)] if inv_bnum != 'All' else df_all.copy()

        # Row 2: floor (scoped to building), then system (scoped to building+floor), then component
        floors_avail  = sorted(df_bldg['floor'].dropna().unique().tolist())
        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            inv_floor = st.selectbox(
                "Floor" + (f" ({len(floors_avail)})" if inv_bnum != 'All' else ""),
                ['All'] + floors_avail, key='inv_floor')

        df_floor = df_bldg[df_bldg['floor'] == inv_floor] if inv_floor != 'All' else df_bldg.copy()
        systems_avail = sorted(df_floor['system_type'].dropna().unique().tolist())
        with r2c2:
            inv_system = st.selectbox(
                "System Type" + (f" ({len(systems_avail)})" if inv_floor != 'All' else ""),
                ['All'] + systems_avail, key='inv_system')

        df_system = df_floor[df_floor['system_type'] == inv_system] if inv_system != 'All' else df_floor.copy()
        comps_avail = sorted(df_system['component'].dropna().unique().tolist())
        with r2c3:
            inv_comp = st.selectbox(
                "Component" + (f" ({len(comps_avail)})" if inv_system != 'All' else ""),
                ['All'] + comps_avail, key='inv_comp')

        # Final filtered dataframe
        df = df_system[df_system['component'] == inv_comp] if inv_comp != 'All' else df_system.copy()
        if inv_search:
            s = inv_search.lower()
            mask = df.apply(lambda row: any(s in str(v).lower() for v in row), axis=1)
            df = df[mask]

        disp = {'bldg_num':'Bldg #','floor':'Floor','room':'Room',
                'system_type':'System Type','component':'Component','address':'Address'}
        df_show = df[[c for c in disp if c in df.columns]].rename(columns=disp)
        st.write(f"**{len(df_show):,}** components — click a row to view photo")

        # Table + photo side by side
        tbl_col, img_col = st.columns([3, 2])
        with tbl_col:
            inv_sel = st.dataframe(df_show, use_container_width=True, hide_index=True,
                                   height=540, on_select="rerun",
                                   selection_mode="single-row", key="inv_tbl")
        with img_col:
            inv_rows = inv_sel.get("selection",{}).get("rows",[]) if inv_sel else []
            if inv_rows and not df.empty:
                row = df.iloc[inv_rows[0]]
                _mb = dbm.get_master_building(str(row.get('bldg_num','')))
                riser_folder = _mb.get('riser_folder','') if _mb else ''
                # Try exact first, then fuzzy
                img_path = dbm.get_component_image_path(
                    bldg_num    = row.get('bldg_num',''),
                    floor       = row.get('floor',''),
                    room        = row.get('room',''),
                    system_type = row.get('system_type',''),
                    component   = row.get('component',''),
                    riser_folder= riser_folder
                )
                if img_path:
                    st.image(img_path,
                             caption=f"{row.get('component','')} — {row.get('floor','')} {row.get('room','')}",
                             use_container_width=True)
                    st.markdown(f"""
                    <div style="background:#f9f9f9;border-radius:6px;padding:8px 12px;font-size:12px">
                    <b>Building:</b> {row.get('bldg_num','')} &nbsp;·&nbsp;
                    <b>Floor:</b> {row.get('floor','')} &nbsp;·&nbsp;
                    <b>Room:</b> {row.get('room','')}<br>
                    <b>System:</b> {row.get('system_type','')} &nbsp;·&nbsp;
                    <b>Component:</b> {row.get('component','')}
                    </div>""", unsafe_allow_html=True)
                else:
                    # Show all fuzzy matches for this component if exact fails
                    fuzzy = dbm.get_component_images_fuzzy(
                        row.get('bldg_num',''), riser_folder, row.get('component',''))
                    if fuzzy:
                        st.image(fuzzy[0][0],
                                 caption=f"{row.get('component','')} — {fuzzy[0][1]} (fuzzy match)",
                                 use_container_width=True)
                    else:
                        st.markdown(f"""
                        <div style="background:#f9f9f9;border-radius:6px;padding:40px 12px;
                        text-align:center;color:#888;font-size:13px">
                        📷 No photo on file<br>
                        <span style="font-size:11px">{row.get('component','')} —
                        {row.get('floor','')} {row.get('room','')}</span>
                        </div>""", unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background:#f9f9f9;border-radius:6px;padding:60px 12px;
                text-align:center;color:#aaa;font-size:13px">
                👆 Click a row to view component photo
                </div>""", unsafe_allow_html=True)

        # Summary tables below the table
        if not df.empty:
            sm1, sm2 = st.columns(2)
            with sm1:
                st.markdown("**By Component**")
                cc = df["component"].value_counts().reset_index()
                cc.columns = ["Component","Count"]
                st.dataframe(cc, use_container_width=True, hide_index=True, height=250)
            with sm2:
                st.markdown("**By System Type**")
                sc = df["system_type"].value_counts().reset_index()
                sc.columns = ["System","Count"]
                st.dataframe(sc, use_container_width=True, hide_index=True, height=250)

    _inventory_tab()


# ══════════════════════════════════════════════════════════════════════════════
# ADD / IMPORT BUILDINGS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "➕  Add / Import Buildings":
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>Add / Import Buildings</h1>
          <p>Add a single building or bulk import from Excel / CSV</p>
        </div>
    </div>''', unsafe_allow_html=True)

    tab_single, tab_import = st.tabs(["➕ Add Single Building", "📥 Bulk Import"])

    with tab_single:
        st.markdown("### New Building")
        with st.form("add_bldg_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                nb_num   = st.text_input("Building Number *", placeholder="e.g. 200")
                nb_name  = st.text_input("Building Name *", placeholder="e.g. Marriott Library")
                nb_addr  = st.text_input("Street Address")
                nb_city  = st.text_input("City", value="Salt Lake City")
                nb_state = st.text_input("State", value="UT")
                nb_zip   = st.text_input("Zip", value="84112")
            with c2:
                nb_dist  = st.text_input("District FA", placeholder="e.g. PRESIDENTS")
                nb_panel = st.text_input("Panel Type", placeholder="e.g. E-3 VOICE")
                nb_month = st.selectbox("Inspection Month", ["","January","February","March","April","May","June","July","August","September","October","November","December"])
                nb_yr    = st.number_input("Year Installed", min_value=1970, max_value=2030, value=2010, step=1)
                nb_sqft  = st.number_input("Sq Ft", min_value=0, value=0, step=100)
                nb_resp  = st.selectbox("Responsibility", ["Campus","Hospital","Research Park","Other"])
            with c3:
                nb_fp    = st.text_input("FocalPoint Name", placeholder="e.g. 200 LIBRARY")
                nb_gw_ip = st.text_input("Gateway IP")
                nb_anx   = st.text_input("ANX IP")
                nb_vlan  = st.text_input("VLAN")
                nb_aux   = st.selectbox("Auxiliary Panel", ["No","Yes"])
                nb_riser = st.text_input("Riser Folder", placeholder="e.g. District1_Presidents")

            nb_photo = st.file_uploader("Building Photo (optional)", type=['jpg','jpeg','png'],
                                         key='nb_photo')
            if st.form_submit_button("💾 Add Building", type="primary"):
                if not nb_num or not nb_name:
                    st.error("Building Number and Name are required.")
                else:
                    fields = {
                        'bldg_num': nb_num.strip(), 'name': nb_name.strip(),
                        'address': nb_addr, 'city': nb_city, 'state': nb_state, 'zip': nb_zip,
                        'district': nb_dist.upper() if nb_dist else '',
                        'panel_type': nb_panel, 'inspection_month': nb_month,
                        'year_installed': int(nb_yr) if nb_yr else None,
                        'sq_ft': int(nb_sqft) if nb_sqft else None,
                        'responsibility': nb_resp, 'focalpoint_name': nb_fp,
                        'gateway_ip': nb_gw_ip, 'anx_ip': nb_anx, 'vlan': nb_vlan,
                        'aux': nb_aux, 'riser_folder': nb_riser,
                    }
                    if nb_photo:
                        import base64 as _b64
                        ext = nb_photo.name.rsplit('.',1)[-1].lower()
                        fields['image_data'] = _b64.b64encode(nb_photo.read()).decode()
                        fields['image_ext'] = ext
                    result = dbm.add_building(fields)
                    if result:
                        st.success(f"✅ Building {nb_num} — {nb_name} added successfully!")
                        st.cache_data.clear()
                    else:
                        st.error("Failed to add building. Check that building number is unique.")

    with tab_import:
        st.markdown("### Bulk Import from Excel / CSV")
        # Template download
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Buildings_Import_Template.xlsx'), 'rb') as _tf:
            st.download_button("⬇️ Download Import Template (.xlsx)",
                data=_tf.read(), file_name="Buildings_Import_Template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.info("""**Expected columns** (column names must match exactly):
        `Building Number`, `Building Name_Bldg`, `District FA`, `Panel Type`, `Inspection Month`,
        `Street Address`, `City`, `State`, `Zip`, `Gross Sq Ft`, `Year Installed`,
        `Gateway Ip Addresses`, `Anx Ip Addresses`, `Vlan`, `FocalPoint Name`, `Riser Inventory Folder`
        
        Extra columns are ignored. Use the Master_Building_Sheet as a template.""")

        up_file = st.file_uploader("Upload Excel (.xlsx) or CSV (.csv)", type=["xlsx","csv"],
                                    key="bldg_import_file")
        overwrite = st.checkbox("Overwrite existing buildings with same Building Number", value=False)

        if up_file:
            try:
                if up_file.name.endswith('.csv'):
                    df_imp = pd.read_csv(up_file)
                else:
                    df_imp = pd.read_excel(up_file)

                st.write(f"**Preview:** {len(df_imp)} rows, {len(df_imp.columns)} columns")
                st.dataframe(df_imp.head(5), use_container_width=True, hide_index=True)

                # Column mapping
                col_map = {
                    'Building Number': 'bldg_num', 'Building Name_Bldg': 'name',
                    'District FA': 'district', 'Panel Type': 'panel_type',
                    'Inspection Month': 'inspection_month', 'Street Address': 'address',
                    'City': 'city', 'State': 'state', 'Zip': 'zip',
                    'Gross Sq Ft': 'sq_ft', 'Year Installed': 'year_installed',
                    'Gateway Ip Addresses': 'gateway_ip', 'Anx Ip Addresses': 'anx_ip',
                    'Vlan': 'vlan', 'FocalPoint Name': 'focalpoint_name',
                    'Riser Inventory Folder': 'riser_folder',
                }
                matched = {k: v for k, v in col_map.items() if k in df_imp.columns}
                st.write(f"**Matched columns:** {list(matched.values())}")

                if st.button("📥 Import Buildings", type="primary"):
                    rows = []
                    for _, row in df_imp.iterrows():
                        r = {}
                        for src, dst in matched.items():
                            v = row.get(src)
                            if pd.isna(v): v = None
                            if dst == 'bldg_num': v = str(int(float(v))) if v else None
                            if dst == 'district' and v: v = str(v).upper()
                            r[dst] = v
                        if r.get('bldg_num'):
                            rows.append(r)
                    if rows:
                        inserted, errors = dbm.import_buildings(rows)
                        if inserted:
                            st.success(f"✅ {inserted} buildings imported successfully!")
                            st.cache_data.clear()
                        if errors:
                            st.error(f"Errors: {errors}")
                    else:
                        st.warning("No valid rows found — check Building Number column exists and has values.")
            except Exception as e:
                st.error(f"Error reading file: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# ADD / IMPORT FA DEVICES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "➕  Add / Import FA Devices":
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>Add / Import Fire Alarm Devices</h1>
          <p>Add a single device or bulk import from FocalPoint export</p>
        </div>
    </div>''', unsafe_allow_html=True)

    tab_single, tab_import = st.tabs(["➕ Add Single Device", "📥 Bulk Import"])

    with tab_single:
        st.markdown("### New FA Device")
        # Get building list from master
        _fa_bldgs = dbm.get_master_buildings()
        _fa_bldgs = dbm.sort_buildings(_fa_bldgs)
        _fa_labels = [f"{b['bldg_num']} — {b.get('name','')}" for b in _fa_bldgs]

        with st.form("add_fa_dev_form"):
            dev_bldg = st.selectbox("Building *", _fa_labels, key="add_fa_bldg")
            c1, c2 = st.columns(2)
            with c1:
                dev_type  = st.selectbox("Device Type *", ["","SD — Smoke Detector","HD — Heat Detector","PS — Pull Station","DD — Duct Detector","WF — Waterflow","TS — Tamper Switch","Trans — Transponder","NOTIF — Notification","AES — AES Panel","Beam — Beam Detector","Ext — Fire Extinguisher","Hood — Hood Suppression","CO2 — CO2 Detector","Vesda — VESDA"], key="add_fa_dev_type")
                dev_point = st.text_input("Point / Address *", placeholder="e.g. 1-001")
            with c2:
                dev_desc  = st.text_input("Description", placeholder="e.g. 1st Floor Lobby")
                dev_addr  = st.text_input("Physical Address / Location")

            if st.form_submit_button("💾 Add Device", type="primary"):
                if not dev_type or not dev_point:
                    st.error("Device Type and Point are required.")
                else:
                    sel_bnum = dev_bldg.split(' — ')[0]
                    sel_bldg = next((b for b in _fa_bldgs if b['bldg_num'] == sel_bnum), {})
                    _dev_type_code = dev_type.split(' — ')[0].strip() if dev_type else ''
                    fields = {
                        'building': sel_bldg.get('focalpoint_name') or sel_bldg.get('name',''),
                        'type':     _dev_type_code,
                        'point':    dev_point.strip(),
                        'description': dev_desc.strip(),
                        'address':  dev_addr.strip(),
                    }
                    result = db.add_device(fields)
                    if result:
                        st.success(f"✅ Device {dev_type} — {dev_point} added to {dev_bldg}!")
                    else:
                        st.error("Failed to add device.")

    with tab_import:
        st.markdown("### Bulk Import from Excel / CSV")
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'FA_Devices_Import_Template.xlsx'), 'rb') as _tf:
            st.download_button("⬇️ Download Import Template (.xlsx)",
                data=_tf.read(), file_name="FA_Devices_Import_Template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key='fa_tmpl_dl')
        st.info("""**Expected columns:**
        `building` (FocalPoint name), `type` (device type), `point` (address/point number), 
        `description` (optional), `address` (optional)
        
        This matches the FocalPoint export format. Building must match the FocalPoint Name in the master list.""")

        up_fa = st.file_uploader("Upload Excel (.xlsx) or CSV (.csv)", type=["xlsx","csv"],
                                  key="fa_dev_import_file")
        if up_fa:
            try:
                if up_fa.name.endswith('.csv'):
                    df_fa = pd.read_csv(up_fa)
                else:
                    df_fa = pd.read_excel(up_fa)

                st.write(f"**Preview:** {len(df_fa)} rows")
                st.dataframe(df_fa.head(5), use_container_width=True, hide_index=True)

                # Normalize column names to lowercase
                df_fa.columns = [c.lower().strip() for c in df_fa.columns]
                required = {'building','type','point'}
                missing = required - set(df_fa.columns)
                if missing:
                    st.error(f"Missing required columns: {missing}")
                else:
                    if st.button("📥 Import Devices", type="primary"):
                        rows = []
                        for _, row in df_fa.iterrows():
                            r = {
                                'building':    str(row.get('building','')).strip(),
                                'type':        str(row.get('type','')).strip().upper(),
                                'point':       str(row.get('point','')).strip(),
                                'description': str(row.get('description','') or '').strip(),
                                'address':     str(row.get('address','') or '').strip(),
                            }
                            if r['building'] and r['type'] and r['point']:
                                rows.append(r)
                        if rows:
                            inserted, errors = db.import_devices(rows)
                            if inserted:
                                st.success(f"✅ {inserted} devices imported!")
                            if errors:
                                st.error(f"Errors: {errors[:3]}")
                        else:
                            st.warning("No valid rows found.")
            except Exception as e:
                st.error(f"Error reading file: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# ADD / IMPORT SP COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "➕  Add / Import SP Components":
    import db_sprinkler as dbs
    st.markdown(f'''<div class="uu-header">
        <img src="data:image/png;base64,{LOGO_B64}" style="height:58px;object-fit:contain;flex-shrink:0">
        <div style="border-left:1px solid #e5e5e5;padding-left:20px">
          <h1>Add / Import Sprinkler Components</h1>
          <p>Add a single component or bulk import from riser inventory export</p>
        </div>
    </div>''', unsafe_allow_html=True)

    tab_single, tab_import = st.tabs(["➕ Add Single Component", "📥 Bulk Import"])

    with tab_single:
        st.markdown("### New Sprinkler Component")
        _sp_bldgs = dbm.get_master_buildings()
        _sp_bldgs = dbm.sort_buildings(_sp_bldgs)
        _sp_labels = [f"{b['bldg_num']} — {b.get('name','')}" for b in _sp_bldgs]

        # Load inventory + NFPA standards for cascading (outside form)
        _sp_inv_all = st.session_state.get('_add_inv_all')
        _sp_nfpa    = st.session_state.get('_add_nfpa_all')
        if _sp_inv_all is None:
            with st.spinner("Loading inventory data..."):
                _sp_inv_all = dbs.get_full_inventory()
                _sp_nfpa    = dbs.get_nfpa25_standards()
                st.session_state['_add_inv_all'] = _sp_inv_all
                st.session_state['_add_nfpa_all'] = _sp_nfpa
        _inv_df = pd.DataFrame(_sp_inv_all) if _sp_inv_all else pd.DataFrame()

        # Build NFPA reference lookup: {component: first reference}
        _nfpa_ref = {}
        for _s in (_sp_nfpa or []):
            _c = _s.get('component','')
            if _c and _c not in _nfpa_ref:
                _nfpa_ref[_c] = _s.get('reference','')

        # All known component types from NFPA standards
        _all_comp_types = sorted(set(s.get('component','') for s in (_sp_nfpa or []) if s.get('component')))

        # ── Row 1: Building ───────────────────────────────────────────────────
        sp_bldg = st.selectbox("Building *", _sp_labels, key="add_sp_bldg")
        sel_bnum_add = sp_bldg.split(' — ')[0]

        # Filter inventory to building
        _inv_bldg = _inv_df[_inv_df['bldg_num'].astype(str) == sel_bnum_add] if not _inv_df.empty else pd.DataFrame()

        # ── Row 2: Floor (from building inventory + "Add New") ────────────────
        _floors_exist = sorted(_inv_bldg['floor'].dropna().unique().tolist()) if not _inv_bldg.empty else []
        _floor_opts = _floors_exist + ["＋ Add new floor..."]
        c1, c2 = st.columns(2)
        with c1:
            sp_floor_sel = st.selectbox(f"Floor ({len(_floors_exist)} in building)",
                                        _floor_opts, key="add_sp_floor_sel")
        with c2:
            sp_floor_new = st.text_input("New floor name", key="add_sp_floor_new",
                                         placeholder="e.g. Roof") if sp_floor_sel == "＋ Add new floor..." else None
        sp_floor = sp_floor_new.strip() if sp_floor_sel == "＋ Add new floor..." and sp_floor_new else (
                   sp_floor_sel if sp_floor_sel != "＋ Add new floor..." else "")

        # ── Row 3: Room (cascaded to floor) ───────────────────────────────────
        _inv_floor = _inv_bldg[_inv_bldg['floor'] == sp_floor] if sp_floor and not _inv_bldg.empty else pd.DataFrame()
        _rooms_exist = sorted(_inv_floor['room'].dropna().unique().tolist()) if not _inv_floor.empty else []
        _room_opts = _rooms_exist + ["＋ Add new room..."]
        c3, c4 = st.columns(2)
        with c3:
            sp_room_sel = st.selectbox(f"Room ({len(_rooms_exist)} on floor)",
                                       _room_opts, key="add_sp_room_sel")
        with c4:
            sp_room_new = st.text_input("New room name", key="add_sp_room_new",
                                        placeholder="e.g. Mechanical") if sp_room_sel == "＋ Add new room..." else None
        sp_room = sp_room_new.strip() if sp_room_sel == "＋ Add new room..." and sp_room_new else (
                  sp_room_sel if sp_room_sel != "＋ Add new room..." else "")

        # ── Row 4: System Type (cascaded to floor) ────────────────────────────
        _inv_room = _inv_floor[_inv_floor['room'] == sp_room] if sp_room and not _inv_floor.empty else _inv_floor
        _sys_exist = sorted(_inv_room['system_type'].dropna().unique().tolist()) if not _inv_room.empty else []
        _sys_opts  = _sys_exist + ["＋ Add new system..."]
        c5, c6 = st.columns(2)
        with c5:
            sp_sys_sel = st.selectbox(f"System Type ({len(_sys_exist)} in room)",
                                      _sys_opts, key="add_sp_sys_sel")
        with c6:
            sp_sys_new = st.text_input("New system type", key="add_sp_sys_new",
                                       placeholder="e.g. WetSystem-2") if sp_sys_sel == "＋ Add new system..." else None
        sp_system = sp_sys_new.strip() if sp_sys_sel == "＋ Add new system..." and sp_sys_new else (
                    sp_sys_sel if sp_sys_sel != "＋ Add new system..." else "")

        # ── Row 5: Component (from NFPA types) + auto-fill reference ─────────
        c7, c8, c9 = st.columns(3)
        with c7:
            sp_comp = st.selectbox("Component *", [""] + _all_comp_types, key="add_sp_comp_sel")
        # Auto-fill NFPA reference when component changes
        _auto_ref = _nfpa_ref.get(sp_comp, '') if sp_comp else ''
        if _auto_ref and st.session_state.get('_last_comp_sel') != sp_comp:
            st.session_state['add_sp_ref_input'] = _auto_ref
            st.session_state['_last_comp_sel'] = sp_comp
        with c8:
            sp_ref = st.text_input("NFPA Reference", key="add_sp_ref_input")
        with c9:
            sp_address = st.text_input("Address / Index", key="add_sp_addr")

        if _auto_ref:
            st.caption(f"📖 NFPA 25 ref for {sp_comp}: **{_auto_ref}**")

        # ── Photo ─────────────────────────────────────────────────────────────
        sp_photo = st.file_uploader("Component Photo (optional)", type=['jpg','jpeg','png'],
                                     key='sp_comp_photo')

        # ── Save button ───────────────────────────────────────────────────────
        if st.button("💾 Add Component", type="primary", key="add_sp_save"):
            if not sp_floor or not sp_system or not sp_comp:
                st.error("Floor, System Type, and Component are required.")
            else:
                fields = {
                    'bldg_num':    sel_bnum_add,
                    'floor':       sp_floor,
                    'room':        sp_room,
                    'system_type': sp_system,
                    'component':   sp_comp,
                    'address':     sp_address.strip() if sp_address else '',
                    'reference':   sp_ref.strip() if sp_ref else '',
                }
                result = dbs.add_sp_component(fields)
                if result:
                    # Clear inventory cache so new component shows up
                    if '_add_inv_all' in st.session_state:
                        del st.session_state['_add_inv_all']
                    st.success(f"✅ {sp_comp} added to {sp_bldg} — {sp_floor} {sp_room}!")
                    # Save photo
                    if sp_photo:
                        import base64 as _b64
                        _mb_sp = dbm.get_master_building(sel_bnum_add)
                        _riser = _mb_sp.get('riser_folder','') if _mb_sp else ''
                        if _riser:
                            _img_dir = os.path.join(
                                os.path.dirname(os.path.abspath(__file__)),
                                "images", "Riser Inventory Pictures",
                                _riser, sel_bnum_add, f"{sp_floor} {sp_room}")
                            os.makedirs(_img_dir, exist_ok=True)
                            _ext = sp_photo.name.rsplit('.',1)[-1].lower()
                            _img_name = f"{sel_bnum_add} {sp_floor} {sp_room} {sp_system} {sp_comp}.{_ext}"
                            with open(os.path.join(_img_dir, _img_name), 'wb') as _f:
                                _f.write(sp_photo.read())
                            dbm.clear_image_cache(sel_bnum_add, _riser)
                            st.info("📷 Photo saved — commit and push to make it permanent.")
                        else:
                            st.warning("No riser folder set for this building — photo not saved.")
                else:
                    st.error("Failed to add component.")

    with tab_import:
        st.markdown("### Bulk Import from Excel / CSV")
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'SP_Components_Import_Template.xlsx'), 'rb') as _tf:
            st.download_button("⬇️ Download Import Template (.xlsx)",
                data=_tf.read(), file_name="SP_Components_Import_Template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key='sp_tmpl_dl')
        st.info("""**Expected columns:**
        `BUILDING` (building number), `FLOOR`, `ROOM`, `SYSTEM TYPE`, `COMPONENT`, 
        `ADDRESS` (optional), `Reference` (optional)
        
        This matches the riser service log format exactly. You can also import directly
        from the `2026_Spring_Fire_Riser_Service_Log.xlsm` (Merge1 sheet).""")

        _sp_bldgs2 = dbm.get_master_buildings()
        _sp_bldgs2 = dbm.sort_buildings(_sp_bldgs2)
        _sp_labels2 = ["All Buildings"] + [f"{b['bldg_num']} — {b.get('name','')}" for b in _sp_bldgs2]

        col_imp1, col_imp2 = st.columns([2,1])
        with col_imp1:
            up_sp = st.file_uploader("Upload Excel (.xlsx/.xlsm) or CSV (.csv)", 
                                      type=["xlsx","xlsm","csv"], key="sp_comp_import_file")
        with col_imp2:
            clear_first = st.checkbox("Clear existing components for building(s) before import", value=False)
            sheet_name  = st.text_input("Sheet name (Excel only)", value="Merge1")

        if up_sp:
            try:
                import io
                file_bytes = up_sp.read()
                if up_sp.name.endswith('.csv'):
                    df_sp = pd.read_csv(io.BytesIO(file_bytes))
                else:
                    df_sp = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name)

                st.write(f"**Preview:** {len(df_sp)} rows, {len(df_sp.columns)} columns")
                st.dataframe(df_sp.head(5), use_container_width=True, hide_index=True)

                col_map_sp = {
                    'BUILDING': 'bldg_num', 'FLOOR': 'floor', 'ROOM': 'room',
                    'SYSTEM TYPE': 'system_type', 'COMPONENT': 'component',
                    'ADDRESS': 'address', 'Reference': 'reference',
                    'INDEX': 'address',  # alternate name
                }
                matched_sp = {k: v for k, v in col_map_sp.items() if k in df_sp.columns}
                missing_req = {'BUILDING','FLOOR','SYSTEM TYPE','COMPONENT'} - set(matched_sp.keys())
                if missing_req:
                    st.error(f"Missing required columns: {missing_req}")
                else:
                    st.write(f"**Matched:** {list(matched_sp.values())}")
                    # Show unique buildings in file
                    bldg_col = [c for c in df_sp.columns if c == 'BUILDING']
                    if bldg_col:
                        uniq_bldgs = sorted(df_sp['BUILDING'].dropna().unique())
                        st.write(f"**Buildings in file:** {len(uniq_bldgs)} — {list(uniq_bldgs[:10])}")

                    if st.button("📥 Import Components", type="primary"):
                        rows_sp = []
                        for _, row in df_sp.iterrows():
                            r = {}
                            for src, dst in matched_sp.items():
                                v = row.get(src)
                                if pd.isna(v) if isinstance(v, float) else (v is None):
                                    v = None
                                if dst == 'bldg_num' and v is not None:
                                    try: v = str(int(float(v)))
                                    except: v = str(v)
                                r[dst] = str(v).strip() if v is not None else ''
                            if r.get('bldg_num') and r.get('component'):
                                rows_sp.append(r)

                        if rows_sp:
                            if clear_first:
                                bldgs_to_clear = list(set(r['bldg_num'] for r in rows_sp))
                                with st.spinner(f"Clearing {len(bldgs_to_clear)} buildings..."):
                                    for bn in bldgs_to_clear:
                                        dbs.delete_sp_components_for_building(bn)

                            with st.spinner(f"Importing {len(rows_sp)} components..."):
                                inserted_sp, errors_sp = dbs.import_sp_components(rows_sp)

                            if inserted_sp:
                                st.success(f"✅ {inserted_sp} components imported!")
                                st.cache_data.clear()
                            if errors_sp:
                                st.error(f"Errors ({len(errors_sp)}): {errors_sp[0]}")
                        else:
                            st.warning("No valid rows found.")
            except Exception as e:
                import traceback
                st.error(f"Error reading file: {e}")
                st.code(traceback.format_exc())


# ══════════════════════════════════════════════════════════════════════════════
# CAMPUS MAP
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🗺️  Campus Map":
    render_header("Campus Building Map", "Inspection status at a glance · Click a building for details")

    all_buildings = dbm.get_master_buildings()
    all_buildings = dbm.sort_buildings(all_buildings)

    # Get schedule status for each building
    fa_schedule = db.get_schedule()

    # Build status lookup: bldg_num → worst status
    bldg_status = {}
    for s in fa_schedule:
        bn = str(s.get('bldg_num','')).split('.')[0]
        status = s.get('status','Pending')
        rank = {'Overdue':0, 'In Progress':1, 'Pending':2, 'Construction':3, 'Complete':4}
        if bn not in bldg_status or rank.get(status,5) < rank.get(bldg_status[bn],5):
            bldg_status[bn] = status

    status_colors = {
        'Complete': '#22c55e', 'In Progress': '#3b82f6',
        'Pending': '#f59e0b', 'Overdue': '#ef4444', 'Construction': '#8b5cf6',
    }

    # Filter
    map_filter = st.selectbox("Filter by Status",
        ['All','Complete','Overdue','Pending','In Progress','Construction'], key='map_filter')

    # ── Geocode buildings from address ────────────────────────────────────
    # Use session_state to cache geocoded coordinates
    import urllib.request, urllib.parse
    import time as _time

    @st.cache_data(ttl=86400, show_spinner="Geocoding building addresses…")
    def _geocode_buildings(building_data_hash):
        """Geocode all buildings using Nominatim. Cached for 24h."""
        coords = {}
        for b in all_buildings:
            bn = str(b.get('bldg_num',''))
            addr = b.get('address','')
            city = b.get('city','Salt Lake City')
            state = b.get('state','UT')
            zipcode = b.get('zip','84112')

            if not addr or not addr.strip():
                continue

            query = f"{addr}, {city}, {state} {zipcode}"
            try:
                url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
                    'q': query, 'format': 'json', 'limit': 1,
                    'viewbox': '-111.87,-111.82,40.74,40.79',  # UofU bounding box
                    'bounded': 0,
                })
                req = urllib.request.Request(url, headers={'User-Agent': 'UU-FireSystems/1.0'})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read())
                if data:
                    coords[bn] = {
                        'lat': float(data[0]['lat']),
                        'lon': float(data[0]['lon']),
                    }
                _time.sleep(1.1)  # Nominatim rate limit: 1 req/sec
            except:
                pass
        return coords

    # Build a stable hash from building addresses to cache against
    _addr_hash = hash(tuple(
        (b.get('bldg_num',''), b.get('address',''))
        for b in all_buildings if b.get('address')
    ))

    # Show two tabs: Map view + List view with campus map links
    tab_map, tab_list = st.tabs(["🗺️ Map View", "📋 List + Campus Map Links"])

    with tab_list:
        # This always works — no geocoding needed
        st.markdown("Click any building number to open it on the **official UofU campus map**.")
        map_data_list = []
        for b in all_buildings:
            bn = str(b.get('bldg_num',''))
            status = bldg_status.get(bn, 'Pending')
            if map_filter != 'All' and status != map_filter:
                continue
            name = b.get('name','') or f"Building {bn}"
            map_data_list.append({
                'bldg_num': bn, 'name': name,
                'district': b.get('district',''),
                'panel': b.get('panel_type',''),
                'status': status,
                'address': b.get('address',''),
                'sp': '🚿' if int(b.get('total_sp_components') or 0) > 0 else '',
                'map_link': f"https://map.utah.edu/?buildingnumber={bn}",
            })

        # Summary
        mc1, mc2, mc3, mc4, mc5 = st.columns(5)
        mc1.metric("Total", len(map_data_list))
        mc2.metric("✅ Complete", sum(1 for d in map_data_list if d['status']=='Complete'))
        mc3.metric("🔴 Overdue", sum(1 for d in map_data_list if d['status']=='Overdue'))
        mc4.metric("🟡 Pending", sum(1 for d in map_data_list if d['status']=='Pending'))
        mc5.metric("🔵 In Progress", sum(1 for d in map_data_list if d['status']=='In Progress'))

        for d in map_data_list:
            color = status_colors.get(d['status'], '#888')
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:12px;padding:8px 12px;'
                f'border-left:4px solid {color};background:#f9f9f9;border-radius:0 6px 6px 0;margin:4px 0">'
                f'<a href="{d["map_link"]}" target="_blank" style="font-weight:800;color:#CC2929;'
                f'font-size:14px;text-decoration:none">#{d["bldg_num"]}</a>'
                f'<span style="flex:1;font-weight:600">{d["name"]}</span>'
                f'<span style="color:#888;font-size:12px">{d["district"]}</span>'
                f'<span style="color:#888;font-size:12px">{d["panel"]}</span>'
                f'<span style="font-size:12px">{d["sp"]}</span>'
                f'<span style="background:{color};color:white;padding:2px 8px;border-radius:12px;'
                f'font-size:11px;font-weight:700">{d["status"]}</span>'
                f'</div>', unsafe_allow_html=True)

    with tab_map:
        st.info("🌐 Geocoding addresses via OpenStreetMap — first load may take a few minutes. Results are cached for 24 hours.")

        with st.spinner("Geocoding building addresses from OpenStreetMap…"):
            coords = _geocode_buildings(_addr_hash)

        if not coords:
            st.warning("No addresses could be geocoded. Make sure buildings have street addresses in the database.")
            st.stop()

        st.success(f"📍 {len(coords)} of {len(all_buildings)} buildings geocoded from their addresses.")

        map_data = []
        for b in all_buildings:
            bn = str(b.get('bldg_num',''))
            if bn not in coords:
                continue
            status = bldg_status.get(bn, 'Pending')
            if map_filter != 'All' and status != map_filter:
                continue

            c = coords[bn]
            name = b.get('name','') or f"Building {bn}"
            map_data.append({
                'bldg_num': bn, 'name': name,
                'lat': c['lat'], 'lon': c['lon'],
                'status': status, 'color': status_colors.get(status, '#888'),
                'district': b.get('district',''),
                'panel': b.get('panel_type',''),
                'has_sprinkler': '🚿' if int(b.get('total_sp_components') or 0) > 0 else '',
            })

        if map_data:
            df_map = pd.DataFrame(map_data)

            # Summary row
            mc1, mc2, mc3, mc4, mc5 = st.columns(5)
            mc1.metric("On Map", len(df_map))
            mc2.metric("✅ Complete", len(df_map[df_map['status']=='Complete']))
            mc3.metric("🔴 Overdue", len(df_map[df_map['status']=='Overdue']))
            mc4.metric("🟡 Pending", len(df_map[df_map['status']=='Pending']))
            mc5.metric("🔵 In Progress", len(df_map[df_map['status']=='In Progress']))

            # Center on average of geocoded points
            center_lat = df_map['lat'].mean()
            center_lon = df_map['lon'].mean()

            fig = px.scatter_mapbox(
                df_map, lat='lat', lon='lon',
                color='status',
                color_discrete_map=status_colors,
                hover_name='name',
                hover_data={'bldg_num':True, 'district':True, 'panel':True, 'status':True,
                            'lat':False, 'lon':False, 'color':False, 'has_sprinkler':True},
                size_max=15,
                zoom=14,
                center={'lat': center_lat, 'lon': center_lon},
                mapbox_style='open-street-map',
                height=620,
            )
            fig.update_traces(marker=dict(size=12, opacity=0.85))
            fig.update_layout(margin=dict(l=0,r=0,t=0,b=0),
                              legend=dict(orientation='h', y=-0.05, font=dict(size=12)))

            selected = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="campus_map")

            # Click handler
            if selected and selected.get("selection",{}).get("points"):
                pt = selected["selection"]["points"][0]
                idx = pt.get("point_index", 0)
                if idx < len(df_map):
                    clicked = df_map.iloc[idx]
                    st.divider()
                    st.markdown(f"### #{clicked['bldg_num']} — {clicked['name']}")
                    ic1, ic2, ic3, ic4 = st.columns(4)
                    ic1.write(f"**District:** {clicked['district']}")
                    ic2.write(f"**Panel:** {clicked['panel']}")
                    ic3.write(f"**Status:** {clicked['status']}")
                    ic4.markdown(f"[🌐 Open on Campus Map](https://map.utah.edu/?buildingnumber={clicked['bldg_num']})")

                    bc1, bc2 = st.columns(2)
                    with bc1:
                        if st.button("🏛️ View Building Details", key=f"map_bldg_{clicked['bldg_num']}", type="primary"):
                            st.session_state['mb_detail_sel'] = f"{clicked['bldg_num']} — {clicked['name']}"
                            st.session_state['nav_target'] = '🏛️  Buildings'
                            st.rerun()
                    with bc2:
                        if st.button("📋 Start Inspection", key=f"map_insp_{clicked['bldg_num']}"):
                            st.session_state['prefill_bldg'] = clicked['bldg_num']
                            st.session_state['nav_target'] = '📋  New Inspection'
                            st.rerun()
        else:
            st.info("No buildings match the selected filter.")

    # District summary
    st.divider()
    st.markdown("**Buildings by District**")
    dist_counts = {}
    for b in all_buildings:
        d = b.get('district','Unknown')
        dist_counts[d] = dist_counts.get(d, 0) + 1
    dist_df = pd.DataFrame([{'District': d, 'Buildings': c} for d, c in sorted(dist_counts.items(), key=lambda x: -x[1])])
    st.dataframe(dist_df, use_container_width=True, hide_index=True, height=250)


# ══════════════════════════════════════════════════════════════════════════════
# DEFICIENCY TRACKER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚠️  Deficiency Tracker":
    render_header("Deficiency Tracker", "Track, manage, and resolve inspection deficiencies across all systems")

    # Pull all FA inspections with deficiencies
    all_inspections = db.get_inspections()
    all_sp_inspections = dbs.get_sprinkler_inspections()

    # Collect deficiencies from FA inspections
    all_defs = []
    for insp in (all_inspections or []):
        raw = insp.get('deficiencies') or '[]'
        if isinstance(raw, list):
            defs = raw
        else:
            try: defs = json.loads(raw)
            except: defs = []
        for d in defs:
            all_defs.append({
                'id': f"FA-{insp['id']}-{d.get('location','')}",
                'source': 'Fire Alarm',
                'building': insp.get('building_name',''),
                'bldg_num': insp.get('bldg_num',''),
                'date_found': insp.get('inspection_date',''),
                'device': d.get('device',''),
                'location': d.get('location',''),
                'issue': d.get('issue',''),
                'part': d.get('part',''),
                'corrected': d.get('corrected','No'),
                'inspector': insp.get('inspector_name',''),
            })

    # Collect deficiencies from SP inspections
    for insp in (all_sp_inspections or []):
        items = dbs.get_sprinkler_inspection_items(insp['id'])
        for it in (items or []):
            if it.get('status') in ('Critical','Non Critical','Impairment'):
                all_defs.append({
                    'id': f"SP-{insp['id']}-{it.get('component','')}",
                    'source': 'Sprinkler',
                    'building': insp.get('bldg_name',''),
                    'bldg_num': insp.get('bldg_num',''),
                    'date_found': insp.get('inspection_date',''),
                    'device': it.get('component',''),
                    'location': f"{it.get('floor','')} {it.get('room','')}".strip(),
                    'issue': f"{it.get('status','')} — {it.get('comments','')}" if it.get('comments') else it.get('status',''),
                    'part': '',
                    'corrected': 'No',
                    'inspector': insp.get('inspector_name',''),
                })

    # Summary cards
    total_defs = len(all_defs)
    open_defs = sum(1 for d in all_defs if d['corrected'] == 'No')
    partial_defs = sum(1 for d in all_defs if d['corrected'] == 'Partial')
    fixed_defs = sum(1 for d in all_defs if d['corrected'] == 'Yes')
    fa_defs = sum(1 for d in all_defs if d['source'] == 'Fire Alarm')
    sp_defs = sum(1 for d in all_defs if d['source'] == 'Sprinkler')

    dc1, dc2, dc3, dc4, dc5, dc6 = st.columns(6)
    dc1.metric("Total Deficiencies", total_defs)
    dc2.metric("🔴 Open", open_defs)
    dc3.metric("🟡 Partial", partial_defs)
    dc4.metric("✅ Fixed", fixed_defs)
    dc5.metric("🔥 Fire Alarm", fa_defs)
    dc6.metric("🚿 Sprinkler", sp_defs)

    # Aging metrics
    if all_defs:
        from datetime import datetime
        today = date.today()
        ages = []
        for d in all_defs:
            if d['corrected'] == 'No' and d['date_found']:
                try:
                    found = datetime.strptime(d['date_found'], '%Y-%m-%d').date()
                    ages.append((today - found).days)
                except: pass
        if ages:
            avg_age = sum(ages) / len(ages)
            max_age = max(ages)
            st.markdown(
                f'<div style="background:#fef2f2;border-left:4px solid #ef4444;padding:12px 16px;'
                f'border-radius:0 8px 8px 0;margin:12px 0;font-size:13px">'
                f'⏱️ <b>{len(ages)} open deficiencies</b> averaging <b>{avg_age:.0f} days</b> old '
                f'(oldest: <b>{max_age} days</b>)</div>', unsafe_allow_html=True)

    st.divider()

    # Filters
    df1, df2, df3 = st.columns([1,1,1])
    with df1:
        def_source = st.selectbox("Source", ['All','Fire Alarm','Sprinkler'], key='def_source')
    with df2:
        def_status = st.selectbox("Status", ['All','Open (No)','Partial','Fixed (Yes)'], key='def_status')
    with df3:
        def_search = st.text_input("Search", placeholder="Building, device, issue…", key='def_search')

    filtered_defs = all_defs
    if def_source != 'All':
        filtered_defs = [d for d in filtered_defs if d['source'] == def_source]
    if def_status == 'Open (No)':
        filtered_defs = [d for d in filtered_defs if d['corrected'] == 'No']
    elif def_status == 'Partial':
        filtered_defs = [d for d in filtered_defs if d['corrected'] == 'Partial']
    elif def_status == 'Fixed (Yes)':
        filtered_defs = [d for d in filtered_defs if d['corrected'] == 'Yes']
    if def_search:
        q = def_search.lower()
        filtered_defs = [d for d in filtered_defs if
                         q in d.get('building','').lower() or
                         q in d.get('device','').lower() or
                         q in d.get('issue','').lower() or
                         q in d.get('location','').lower()]

    if filtered_defs:
        def_df = pd.DataFrame([{
            'Source':   d['source'],
            'Building': f"#{d['bldg_num']} {d['building']}",
            'Date':     d['date_found'],
            'Device':   d['device'],
            'Location': d['location'],
            'Issue':    d['issue'],
            'Part #':   d['part'],
            'Status':   d['corrected'],
        } for d in filtered_defs])

        def _color_status(val):
            if val == 'No': return 'background-color:#fee2e2;color:#991b1b;font-weight:bold'
            if val == 'Yes': return 'background-color:#dcfce7;color:#166534;font-weight:bold'
            if val == 'Partial': return 'background-color:#fef9c3;color:#854d0e;font-weight:bold'
            return ''

        styled_def = def_df.style.map(_color_status, subset=['Status'])
        st.dataframe(styled_def, use_container_width=True, hide_index=True, height=500)
    else:
        st.success("🎉 No deficiencies found matching your filters. Nice work!")

    # Deficiencies by building chart
    if all_defs:
        st.divider()
        st.markdown("**Open Deficiencies by Building**")
        open_by_bldg = {}
        for d in all_defs:
            if d['corrected'] == 'No':
                key = f"#{d['bldg_num']} {d['building']}"
                open_by_bldg[key] = open_by_bldg.get(key, 0) + 1
        if open_by_bldg:
            sorted_bldgs = sorted(open_by_bldg.items(), key=lambda x: -x[1])[:20]
            bldg_names = [x[0] for x in sorted_bldgs]
            bldg_counts = [x[1] for x in sorted_bldgs]
            fig_def = go.Figure(go.Bar(
                y=bldg_names[::-1], x=bldg_counts[::-1],
                orientation='h', marker_color='#ef4444',
                text=bldg_counts[::-1], textposition='auto'))
            fig_def.update_layout(height=max(300, len(sorted_bldgs)*28),
                                  margin=dict(l=0,r=0,t=10,b=0),
                                  plot_bgcolor='white', paper_bgcolor='white',
                                  xaxis=dict(showgrid=True, gridcolor='#f0f0f0'))
            st.plotly_chart(fig_def, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈  Analytics":
    render_header("Fire Systems Analytics", "Trends, breakdowns, and insights across all campus fire systems")

    stats = db.get_dashboard_stats()
    sp_stats = dbs.get_sprinkler_dashboard_stats()
    all_buildings = dbm.get_master_buildings()

    # ── Inspection Completion Over Time ────────────────────────────────────
    st.markdown('<div class="section-title">Inspection Completion — Cumulative</div>', unsafe_allow_html=True)
    _mdata = {r['month']: r for r in stats.get('by_month', [])}
    cumulative_done = []
    cumulative_total = []
    running_done = 0
    running_total = 0
    for m in MONTHS_NO_ALL:
        md = _mdata.get(m, {})
        running_done += md.get('complete', 0)
        running_total += md.get('total', 0)
        cumulative_done.append(running_done)
        cumulative_total.append(running_total)

    fig_cum = go.Figure()
    fig_cum.add_trace(go.Scatter(x=MONTHS_NO_ALL, y=cumulative_total, name='Scheduled (cumulative)',
                                  mode='lines', line=dict(color='#CC2929', width=2, dash='dot')))
    fig_cum.add_trace(go.Scatter(x=MONTHS_NO_ALL, y=cumulative_done, name='Completed (cumulative)',
                                  mode='lines+markers', line=dict(color='#22c55e', width=3),
                                  fill='tozeroy', fillcolor='rgba(34,197,94,0.1)'))
    # Mark current month
    cur_month = datetime.now().strftime('%B')
    if cur_month in MONTHS_NO_ALL:
        cur_idx = MONTHS_NO_ALL.index(cur_month)
        fig_cum.add_vline(x=cur_idx, line_dash="dash", line_color="#888", opacity=0.5,
                          annotation_text="Today", annotation_position="top right")
    fig_cum.update_layout(height=320, margin=dict(l=0,r=0,t=10,b=0),
                          plot_bgcolor='white', paper_bgcolor='white',
                          legend=dict(orientation='h', y=-0.15),
                          yaxis=dict(showgrid=True, gridcolor='#f0f0f0'))
    st.plotly_chart(fig_cum, use_container_width=True)

    # ── System Age Distribution ───────────────────────────────────────────
    an1, an2 = st.columns(2)
    with an1:
        st.markdown('<div class="section-title">System Age Distribution</div>', unsafe_allow_html=True)
        ages = [int(b.get('age') or 0) for b in all_buildings if b.get('age')]
        if ages:
            fig_age = go.Figure(go.Histogram(
                x=ages, nbinsx=20,
                marker_color=['#22c55e' if a < 10 else '#f59e0b' if a < 15 else '#ef4444' for a in sorted(ages)],
                marker_line_color='white', marker_line_width=1))
            fig_age.add_vrect(x0=15, x1=max(ages)+1, fillcolor='rgba(239,68,68,0.08)',
                              line_width=0, annotation_text="⚠️ >15 yrs", annotation_position="top left")
            fig_age.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0),
                                  plot_bgcolor='white', paper_bgcolor='white',
                                  xaxis_title="System Age (years)", yaxis_title="Buildings",
                                  xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#f0f0f0'))
            # Use simple green color for histogram since per-bar coloring is complex
            fig_age.update_traces(marker_color='#CC2929')
            st.plotly_chart(fig_age, use_container_width=True)

            # Age summary
            old_20 = sum(1 for a in ages if a >= 20)
            old_15 = sum(1 for a in ages if 15 <= a < 20)
            st.markdown(
                f'<div style="font-size:12px;padding:8px;background:#f9f9f9;border-radius:6px">'
                f'🔴 <b>{old_20}</b> systems ≥20 yrs &nbsp;·&nbsp; '
                f'🟠 <b>{old_15}</b> systems 15-19 yrs &nbsp;·&nbsp; '
                f'Average age: <b>{sum(ages)/len(ages):.1f}</b> yrs</div>',
                unsafe_allow_html=True)

    with an2:
        st.markdown('<div class="section-title">Buildings by Panel Type</div>', unsafe_allow_html=True)
        panel_counts = {}
        for b in all_buildings:
            pt = b.get('panel_type','Unknown') or 'Unknown'
            panel_counts[pt] = panel_counts.get(pt, 0) + 1
        if panel_counts:
            sorted_panels = sorted(panel_counts.items(), key=lambda x: -x[1])
            colors_panel = ['#CC2929','#1e40af','#166534','#854d0e','#7c3aed','#0891b2','#be185d','#065f46']
            fig_panel = go.Figure(go.Pie(
                labels=[p[0] for p in sorted_panels],
                values=[p[1] for p in sorted_panels],
                marker=dict(colors=colors_panel[:len(sorted_panels)]),
                hole=0.4, textinfo='label+value',
                textfont=dict(size=11)))
            fig_panel.update_layout(height=320, margin=dict(l=0,r=0,t=10,b=30),
                                    showlegend=False)
            st.plotly_chart(fig_panel, use_container_width=True)

    # ── District Breakdown ────────────────────────────────────────────────
    st.markdown('<div class="section-title">Buildings by District</div>', unsafe_allow_html=True)
    dist_data = {}
    for b in all_buildings:
        d = b.get('district','Unknown') or 'Unknown'
        if d not in dist_data:
            dist_data[d] = {'buildings':0, 'init_devices':0, 'sp_components':0, 'avg_age':[]}
        dist_data[d]['buildings'] += 1
        dist_data[d]['init_devices'] += int(b.get('init_devices') or 0)
        dist_data[d]['sp_components'] += int(b.get('total_sp_components') or 0)
        if b.get('age'): dist_data[d]['avg_age'].append(int(b['age']))

    dist_df = pd.DataFrame([{
        'District': d,
        'Buildings': v['buildings'],
        'Init Devices': v['init_devices'],
        'SP Components': v['sp_components'],
        'Avg Age': f"{sum(v['avg_age'])/len(v['avg_age']):.1f}" if v['avg_age'] else '—',
    } for d, v in sorted(dist_data.items(), key=lambda x: -x[1]['buildings'])])
    st.dataframe(dist_df, use_container_width=True, hide_index=True)

    # ── Devices by Type ───────────────────────────────────────────────────
    st.markdown('<div class="section-title">Device Counts by Type (Campus-Wide)</div>', unsafe_allow_html=True)
    dev_types = {}
    for b in all_buildings:
        for key, label in [('smoke','Smoke'), ('heat','Heat'), ('pull','Pull Station'),
                           ('duct','Duct'), ('init_devices','Init (Total)'),
                           ('notif_devices','Notif (Total)'), ('transponders','Transponders')]:
            v = int(b.get(key) or 0)
            dev_types[label] = dev_types.get(label, 0) + v

    if dev_types:
        sorted_devs = sorted(dev_types.items(), key=lambda x: -x[1])
        fig_dev = go.Figure(go.Bar(
            x=[d[0] for d in sorted_devs],
            y=[d[1] for d in sorted_devs],
            marker_color='#CC2929',
            text=[f"{d[1]:,}" for d in sorted_devs],
            textposition='outside'))
        fig_dev.update_layout(height=300, margin=dict(l=0,r=0,t=20,b=0),
                              plot_bgcolor='white', paper_bgcolor='white',
                              yaxis=dict(showgrid=True, gridcolor='#f0f0f0'))
        st.plotly_chart(fig_dev, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT REPORTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📥  Export Reports":
    render_header("Export Reports", "Download inspection data as Excel spreadsheets")

    st.markdown("### Choose what to export")

    ex1, ex2 = st.columns(2)

    with ex1:
        st.markdown("**🔥 Fire Alarm**")

        # FA inspection summary export
        if st.button("📥 Export FA Inspection History", use_container_width=True, type="primary"):
            inspections = db.get_inspections()
            if inspections:
                export_rows = []
                for insp in inspections:
                    raw = insp.get('deficiencies') or '[]'
                    if isinstance(raw, list): defs = raw
                    else:
                        try: defs = json.loads(raw)
                        except: defs = []
                    export_rows.append({
                        'Building #': insp.get('bldg_num',''),
                        'Building Name': insp.get('building_name',''),
                        'District': insp.get('district',''),
                        'Date': insp.get('inspection_date',''),
                        'Type': insp.get('inspection_type',''),
                        'Result': insp.get('result',''),
                        '% Tested': insp.get('pct_tested',0),
                        'Inspector': insp.get('inspector_name',''),
                        'Work Order': insp.get('work_order',''),
                        'Deficiencies': len(defs),
                        'PS Total': insp.get('ps_total',0), 'PS Tested': insp.get('ps_tested',0),
                        'SD Total': insp.get('sd_total',0), 'SD Tested': insp.get('sd_tested',0),
                        'HD Total': insp.get('hd_total',0), 'HD Tested': insp.get('hd_tested',0),
                        'DD Total': insp.get('dd_total',0), 'DD Tested': insp.get('dd_tested',0),
                        'Notes': insp.get('notes',''),
                    })
                export_df = pd.DataFrame(export_rows)
                import io
                buf = io.BytesIO()
                export_df.to_excel(buf, index=False, sheet_name='FA Inspections')
                st.download_button("⬇️ Download FA Inspections.xlsx", data=buf.getvalue(),
                                   file_name=f"FA_Inspections_{date.today().isoformat()}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("No FA inspections to export.")

        # FA schedule export
        if st.button("📥 Export FA Schedule", use_container_width=True):
            schedule = db.get_schedule()
            if schedule:
                sched_df = pd.DataFrame([{
                    'Building #': s.get('bldg_num',''),
                    'Building': s.get('building_name',''),
                    'Month': s.get('month',''),
                    'Status': s.get('status',''),
                    'District': s.get('district',''),
                    'Est Hours': s.get('est_hours',''),
                    'Date Completed': s.get('date_completed',''),
                    'Uploaded CMS': s.get('uploaded_cms',''),
                    'Notes': s.get('notes',''),
                } for s in schedule])
                import io
                buf = io.BytesIO()
                sched_df.to_excel(buf, index=False, sheet_name='FA Schedule')
                st.download_button("⬇️ Download FA Schedule.xlsx", data=buf.getvalue(),
                                   file_name=f"FA_Schedule_{date.today().isoformat()}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("No schedule data to export.")

    with ex2:
        st.markdown("**🚿 Sprinkler**")

        # SP inspection history export
        if st.button("📥 Export SP Inspection History", use_container_width=True, type="primary"):
            sp_inspections = dbs.get_sprinkler_inspections()
            if sp_inspections:
                sp_rows = []
                for insp in sp_inspections:
                    items = dbs.get_sprinkler_inspection_items(insp['id'])
                    n_pass = sum(1 for it in (items or []) if it.get('status') == 'Pass')
                    n_crit = sum(1 for it in (items or []) if it.get('status') in ('Critical','Non Critical','Impairment'))
                    sp_rows.append({
                        'Building #': insp.get('bldg_num',''),
                        'Building': insp.get('bldg_name',''),
                        'Date': insp.get('inspection_date',''),
                        'Frequency': insp.get('freq_type',''),
                        'Result': insp.get('overall_result',''),
                        'Inspector': insp.get('inspector_name',''),
                        'Items Total': len(items or []),
                        'Pass': n_pass,
                        'Deficiencies': n_crit,
                        'Notes': insp.get('notes',''),
                    })
                sp_df = pd.DataFrame(sp_rows)
                import io
                buf = io.BytesIO()
                sp_df.to_excel(buf, index=False, sheet_name='SP Inspections')
                st.download_button("⬇️ Download SP Inspections.xlsx", data=buf.getvalue(),
                                   file_name=f"SP_Inspections_{date.today().isoformat()}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("No SP inspections to export.")

        # SP schedule export
        if st.button("📥 Export SP Schedule", use_container_width=True):
            sp_sched = dbs.get_sprinkler_schedule()
            if sp_sched:
                sp_sched_df = pd.DataFrame([{
                    'Building #': s.get('bldg_num',''),
                    'Month': s.get('month',''),
                    'Frequency': s.get('freq_type',''),
                    'Status': s.get('status',''),
                    'Date Completed': s.get('date_completed',''),
                    'Notes': s.get('notes',''),
                } for s in sp_sched])
                import io
                buf = io.BytesIO()
                sp_sched_df.to_excel(buf, index=False, sheet_name='SP Schedule')
                st.download_button("⬇️ Download SP Schedule.xlsx", data=buf.getvalue(),
                                   file_name=f"SP_Schedule_{date.today().isoformat()}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("No SP schedule data to export.")

    # Sprinkler Quarterly Report — Building, Name, Date, SystemRiser Reading
    st.divider()
    st.markdown("**🚿 Sprinkler Quarterly Riser Report**")
    st.caption("Building Number, Building Name, Quarterly Inspection Date, SystemRiser Reading")

    rpt_c1, rpt_c2 = st.columns([1, 1])
    with rpt_c1:
        _rpt_seasons = ['All', 'Fall 2025', 'Winter 2025/2026', 'Spring 2026', 'Summer 2026']
        rpt_season = st.selectbox("Filter by Season / Period", _rpt_seasons, key='rpt_sp_season')
    with rpt_c2:
        _rpt_fiscal = st.selectbox("Fiscal Year", ['FY2026 (Jul 2025 – Jun 2026)', 'FY2025 (Jul 2024 – Jun 2025)', 'All Time'],
                                    key='rpt_sp_fy')

    if st.button("📥 Generate Sprinkler Quarterly Riser Report", use_container_width=True, type="primary"):
        # Get all SP inspections
        sp_all = dbs.get_sprinkler_inspections()
        bldg_names_map = {str(b.get('bldg_num','')): b.get('name','') for b in dbm.get_master_buildings()}

        # Filter by fiscal year
        if 'FY2026' in _rpt_fiscal:
            sp_all = [i for i in sp_all if i.get('inspection_date','') >= '2025-07-01' and i.get('inspection_date','') <= '2026-06-30']
        elif 'FY2025' in _rpt_fiscal:
            sp_all = [i for i in sp_all if i.get('inspection_date','') >= '2024-07-01' and i.get('inspection_date','') <= '2025-06-30']

        # Filter by season
        if rpt_season == 'Fall 2025':
            sp_all = [i for i in sp_all if '2025-09' <= i.get('inspection_date','')[:7] <= '2025-11']
        elif rpt_season == 'Winter 2025/2026':
            sp_all = [i for i in sp_all if i.get('inspection_date','')[:7] in ('2025-12','2026-01','2026-02')]
        elif rpt_season == 'Spring 2026':
            sp_all = [i for i in sp_all if i.get('inspection_date','')[:7] in ('2026-03','2026-04','2026-05')]
        elif rpt_season == 'Summer 2026':
            sp_all = [i for i in sp_all if i.get('inspection_date','')[:7] in ('2026-06','2026-07','2026-08')]

        # For each inspection, find SystemRiser readings
        rpt_rows = []
        for insp in sp_all:
            items = dbs.get_sprinkler_inspection_items(insp['id'])
            # Find SystemRiser items with readings
            riser_items = [it for it in (items or []) if
                           it.get('component','') == 'SystemRiser' and it.get('reading','')]
            bldg_num = str(insp.get('bldg_num',''))
            bldg_name = insp.get('bldg_name','') or bldg_names_map.get(bldg_num, '')

            if riser_items:
                for ri in riser_items:
                    rpt_rows.append({
                        'Building Number': bldg_num,
                        'Building Name': bldg_name,
                        'Inspection Date': insp.get('inspection_date',''),
                        'Inspector': insp.get('inspector_name',''),
                        'Frequency': insp.get('freq_type',''),
                        'System': ri.get('system_type',''),
                        'Floor / Room': f"{ri.get('floor','')} {ri.get('room','')}".strip(),
                        'SystemRiser Reading': ri.get('reading',''),
                        'Status': ri.get('status',''),
                        'Comments': ri.get('comments',''),
                        'Overall Result': insp.get('overall_result',''),
                    })
            else:
                # Still include buildings without riser readings
                rpt_rows.append({
                    'Building Number': bldg_num,
                    'Building Name': bldg_name,
                    'Inspection Date': insp.get('inspection_date',''),
                    'Inspector': insp.get('inspector_name',''),
                    'Frequency': insp.get('freq_type',''),
                    'System': '',
                    'Floor / Room': '',
                    'SystemRiser Reading': '— no reading —',
                    'Status': '',
                    'Comments': '',
                    'Overall Result': insp.get('overall_result',''),
                })

        if rpt_rows:
            rpt_df = pd.DataFrame(rpt_rows)
            # Sort by building number
            rpt_df['_sort'] = rpt_df['Building Number'].apply(
                lambda x: int(x) if str(x).isdigit() else 9999)
            rpt_df = rpt_df.sort_values(['_sort','Inspection Date']).drop(columns=['_sort'])

            st.write(f"**{len(rpt_df)} rows** across {rpt_df['Building Number'].nunique()} buildings")
            st.dataframe(rpt_df, use_container_width=True, hide_index=True, height=400)

            import io
            buf = io.BytesIO()
            rpt_df.to_excel(buf, index=False, sheet_name='Quarterly Riser Report')
            _fy_label = _rpt_fiscal.split(' ')[0] if _rpt_fiscal != 'All Time' else 'AllTime'
            _season_label = rpt_season.replace(' ','_').replace('/','_')
            st.download_button("⬇️ Download Quarterly Riser Report.xlsx",
                               data=buf.getvalue(),
                               file_name=f"SP_Quarterly_Riser_Report_{_fy_label}_{_season_label}_{date.today().isoformat()}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("No sprinkler inspections found for the selected period.")

    # Combined deficiency export
    st.divider()
    st.markdown("**⚠️ Combined Deficiency Report**")
    if st.button("📥 Export All Deficiencies", use_container_width=True, type="primary"):
        all_inspections = db.get_inspections()
        all_sp_inspections = dbs.get_sprinkler_inspections()
        def_rows = []
        for insp in (all_inspections or []):
            raw = insp.get('deficiencies') or '[]'
            if isinstance(raw, list): defs = raw
            else:
                try: defs = json.loads(raw)
                except: defs = []
            for d in defs:
                def_rows.append({
                    'Source': 'Fire Alarm',
                    'Building #': insp.get('bldg_num',''),
                    'Building': insp.get('building_name',''),
                    'Date Found': insp.get('inspection_date',''),
                    'Device': d.get('device',''),
                    'Location': d.get('location',''),
                    'Issue': d.get('issue',''),
                    'Part #': d.get('part',''),
                    'Corrected': d.get('corrected','No'),
                    'Inspector': insp.get('inspector_name',''),
                })
        for insp in (all_sp_inspections or []):
            items = dbs.get_sprinkler_inspection_items(insp['id'])
            for it in (items or []):
                if it.get('status') in ('Critical','Non Critical','Impairment'):
                    def_rows.append({
                        'Source': 'Sprinkler',
                        'Building #': insp.get('bldg_num',''),
                        'Building': insp.get('bldg_name',''),
                        'Date Found': insp.get('inspection_date',''),
                        'Device': it.get('component',''),
                        'Location': f"{it.get('floor','')} {it.get('room','')}".strip(),
                        'Issue': f"{it.get('status','')} — {it.get('comments','')}",
                        'Part #': '',
                        'Corrected': 'No',
                        'Inspector': insp.get('inspector_name',''),
                    })
        if def_rows:
            def_df = pd.DataFrame(def_rows)
            import io
            buf = io.BytesIO()
            def_df.to_excel(buf, index=False, sheet_name='Deficiencies')
            st.download_button("⬇️ Download Deficiencies.xlsx", data=buf.getvalue(),
                               file_name=f"All_Deficiencies_{date.today().isoformat()}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.success("No deficiencies found across all inspections. 🎉")

    # Building master export
    st.divider()
    st.markdown("**🏛️ Building Master List**")
    if st.button("📥 Export Building Master List", use_container_width=True):
        all_b = dbm.get_master_buildings()
        if all_b:
            bldg_df = pd.DataFrame([{
                'Building #': b.get('bldg_num',''),
                'Name': b.get('name',''),
                'District': b.get('district',''),
                'Address': b.get('address',''),
                'Panel Type': b.get('panel_type',''),
                'Year Installed': b.get('year_installed',''),
                'Age': b.get('age',''),
                'Inspection Month': b.get('inspection_month',''),
                'Init Devices': b.get('init_devices',''),
                'Notif Devices': b.get('notif_devices',''),
                'Smoke': b.get('smoke',''),
                'Heat': b.get('heat',''),
                'Pull': b.get('pull',''),
                'Duct': b.get('duct',''),
                'SP Components': b.get('total_sp_components',''),
                'Gateway IP': b.get('gateway_ip',''),
                'FocalPoint': b.get('focalpoint_name',''),
            } for b in dbm.sort_buildings(all_b)])
            import io
            buf = io.BytesIO()
            bldg_df.to_excel(buf, index=False, sheet_name='Buildings')
            st.download_button("⬇️ Download Buildings.xlsx", data=buf.getvalue(),
                               file_name=f"Building_Master_{date.today().isoformat()}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


elif page == "🖨️  Print Report":
    import db_sprinkler as dbs

    # ── Sprinkler inspection print ────────────────────────────────────────────
    _last_type = st.session_state.get('last_print_type', 'fa')
    sp_pdata = st.session_state.get('sp_print_data')
    if sp_pdata and _last_type == 'sp':

        # Load items if not already in pdata
        sp_items = sp_pdata.get('items') or []
        if not sp_items and sp_pdata.get('insp_id'):
            sp_items = dbs.get_sprinkler_inspection_items(sp_pdata['insp_id'])

        # Counts
        n_pass    = sum(1 for it in sp_items if it.get('status') == 'Pass')
        n_crit    = sum(1 for it in sp_items if it.get('status') == 'Critical')
        n_noncrit = sum(1 for it in sp_items if it.get('status') == 'Non Critical')
        n_imp     = sum(1 for it in sp_items if it.get('status') == 'Impairment')
        n_na      = sum(1 for it in sp_items if it.get('status') == 'N/A')
        n_total   = len(sp_items)

        sp_result  = sp_pdata.get('result','')
        res_clean  = sp_result.split('—')[0].strip()
        res_bg     = '#dcfce7' if 'PASS' in sp_result else ('#fee2e2' if 'FAIL' in sp_result else '#fef9c3')
        res_color  = '#166534' if 'PASS' in sp_result else ('#991b1b' if 'FAIL' in sp_result else '#854d0e')

        # Building info from master
        sp_bldg = dbm.get_master_building(sp_pdata.get('bldg_num',''))
        addr_str = ', '.join(filter(None,[sp_bldg.get('address',''), sp_bldg.get('city',''), sp_bldg.get('state','')]))

        # Logo
        logo_html = '<img src="data:image/png;base64,{}" style="height:80px;object-fit:contain">'.format(
            LOGO_B64_PRINT if LOGO_B64_PRINT else LOGO_B64)

        # Building image
        bldg_img_html = ''
        img_b64, img_ext = dbm.get_building_image(sp_pdata.get('bldg_num',''))
        if img_b64:
            bldg_img_html = '<img src="data:image/{};base64,{}" style="width:100%;max-height:180px;object-fit:cover;border-radius:6px;margin-top:10px">'.format(img_ext, img_b64)

        # Items table rows grouped by system
        from itertools import groupby
        sp_items_sorted = sorted(sp_items, key=lambda x: (x.get('system_type',''), x.get('component','')))

        def status_badge(s):
            if s == 'Pass':         return '<span class="badge-pass">Pass</span>'
            if s == 'Critical':     return '<span class="badge-fail">Critical</span>'
            if s == 'Non Critical': return '<span class="badge-partial">Non Critical</span>'
            if s == 'Impairment':   return '<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700">Impairment</span>'
            return f'<span style="background:#f3f4f6;color:#555;padding:2px 8px;border-radius:12px;font-size:11px">{s}</span>'

        items_rows = ''
        for it in sp_items_sorted:
            loc = f"{it.get('floor','')} {it.get('room','')}".strip()
            items_rows += '<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td style="font-size:10px;max-width:180px">{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(
                it.get('system_type',''), it.get('component',''), loc,
                it.get('procedure',''), it.get('criteria',''),
                status_badge(it.get('status','')),
                it.get('reading','') or '—',
                it.get('comments','') or '—'
            )

        # Deficiencies
        defects = [it for it in sp_items if it.get('status') in ('Critical','Non Critical','Impairment')]
        if defects:
            def_rows = ''
            for d in defects:
                loc = f"{d.get('floor','')} {d.get('room','')}".strip()
                def_rows += '<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(
                    d.get('system_type',''), d.get('component',''), loc,
                    status_badge(d.get('status','')), d.get('reading','') or '—', d.get('comments','') or '—')
            def_html = ('<table class="rpt-table"><thead><tr>'
                        '<th>System</th><th>Component</th><th>Location</th>'
                        '<th>Status</th><th>Reading</th><th>Comments</th>'
                        '</tr></thead><tbody>' + def_rows + '</tbody></table>')
        else:
            def_html = '<p style="color:#888;font-style:italic;font-size:12px">No deficiencies recorded.</p>'

        # Print CSS
        st.markdown("""
        <style>
        @media print {
            [data-testid="stSidebar"],[data-testid="stHeader"],
            [data-testid="stToolbar"],[data-testid="stBottom"],
            .stButton, footer, .no-print { display: none !important; }
            .block-container { padding: 0 !important; max-width: 100% !important; margin: 0 !important; }
            body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
        }
        .print-page { font-family: Arial, sans-serif; max-width: 960px; margin: 0 auto; }
        .rpt-header { border-bottom: 3px solid #0369a1; padding: 16px 0; margin-bottom: 20px;
                      display: flex; align-items: center; justify-content: space-between; gap: 16px; }
        .rpt-section { border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px 16px; margin-bottom: 14px; }
        .rpt-section-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;
                             color: #0369a1; border-bottom: 1px solid #e5e7eb; padding-bottom: 7px; margin-bottom: 11px; }
        .rpt-grid  { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .rpt-field { padding: 8px 10px; background: #f9f9f9; border-radius: 6px; border-left: 3px solid #0369a1; }
        .rpt-label { font-size: 10px; color: #888; text-transform: uppercase; font-weight: 600; }
        .rpt-val   { font-size: 13px; color: #111; font-weight: 600; margin-top: 2px; }
        .rpt-table { width: 100%; border-collapse: collapse; font-size: 11px; }
        .rpt-table th { background: #0369a1; color: white; padding: 7px 10px; text-align: left; }
        .rpt-table td { padding: 5px 8px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }
        .rpt-table tr:nth-child(even) td { background: #f9f9f9; }
        .badge-pass    { background:#dcfce7; color:#166534; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:700; }
        .badge-fail    { background:#fee2e2; color:#991b1b; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:700; }
        .badge-partial { background:#fef9c3; color:#854d0e; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:700; }
        .result-badge  { font-size: 20px; font-weight: 900; padding: 10px 20px; border-radius: 8px; }
        .sig-line { border-bottom: 1px solid #333; height: 32px; margin-bottom: 4px; }
        .sp-summary { display:grid; grid-template-columns:repeat(6,1fr); gap:8px; margin:12px 0; }
        .sp-stat { text-align:center; padding:10px 4px; border-radius:8px; border:1px solid #e5e7eb; }
        .sp-stat-num { font-size:22px; font-weight:800; }
        .sp-stat-lbl { font-size:10px; color:#888; text-transform:uppercase; font-weight:600; margin-top:2px; }
        </style>""", unsafe_allow_html=True)

        # Assemble HTML report
        html_parts = [
            '<div class="print-page">',

            # Header
            '<div class="rpt-header">',
            logo_html,
            '<div style="flex:1;padding-left:20px;border-left:1px solid #e5e5e5">',
            '<div style="font-size:20px;font-weight:800;color:#1a1a1a">Sprinkler System Inspection Report</div>',
            '<div style="font-size:11px;color:#888;margin-top:4px">NFPA 25 &nbsp;·&nbsp; University of Utah &nbsp;·&nbsp; Facilities Management</div>',
            '</div>',
            '<div class="result-badge" style="background:{};color:{}">'.format(res_bg, res_color),
            res_clean, '</div></div>',

            # Building info
            '<div class="rpt-section">',
            '<div class="rpt-section-title">Building Information</div>',
            '<div style="display:grid;grid-template-columns:2fr 1fr;gap:16px">',
            '<div class="rpt-grid">',
            '<div class="rpt-field"><div class="rpt-label">Building Name</div><div class="rpt-val">{}</div></div>'.format(sp_pdata.get('bldg_name','—')),
            '<div class="rpt-field"><div class="rpt-label">Building #</div><div class="rpt-val">{}</div></div>'.format(sp_pdata.get('bldg_num','—')),
            '<div class="rpt-field"><div class="rpt-label">Address</div><div class="rpt-val">{}</div></div>'.format(addr_str or '—'),
            '<div class="rpt-field"><div class="rpt-label">District</div><div class="rpt-val">{}</div></div>'.format(sp_bldg.get('district','—')),
            '<div class="rpt-field"><div class="rpt-label">Inspection Date</div><div class="rpt-val">{}</div></div>'.format(sp_pdata.get('date','—')),
            '<div class="rpt-field"><div class="rpt-label">Frequency</div><div class="rpt-val">{}</div></div>'.format(sp_pdata.get('freq_type','—')),
            '<div class="rpt-field"><div class="rpt-label">Inspector</div><div class="rpt-val">{}</div></div>'.format(sp_pdata.get('inspector','—')),
            '<div class="rpt-field"><div class="rpt-label">AIM Asset #</div><div class="rpt-val">{}</div></div>'.format(sp_bldg.get('aim_asset','—')),
            '</div>',
            '<div>' + bldg_img_html + '</div>',
            '</div></div>',

            # Summary
            '<div class="rpt-section">',
            '<div class="rpt-section-title">Inspection Summary</div>',
            '<div class="sp-summary">',
            '<div class="sp-stat"><div class="sp-stat-num">{}</div><div class="sp-stat-lbl">Total</div></div>'.format(n_total),
            '<div class="sp-stat" style="border-color:#166534"><div class="sp-stat-num" style="color:#166534">{}</div><div class="sp-stat-lbl">Pass</div></div>'.format(n_pass),
            '<div class="sp-stat" style="border-color:#991b1b"><div class="sp-stat-num" style="color:#991b1b">{}</div><div class="sp-stat-lbl">Critical</div></div>'.format(n_crit),
            '<div class="sp-stat" style="border-color:#854d0e"><div class="sp-stat-num" style="color:#854d0e">{}</div><div class="sp-stat-lbl">Non Critical</div></div>'.format(n_noncrit),
            '<div class="sp-stat" style="border-color:#92400e"><div class="sp-stat-num" style="color:#92400e">{}</div><div class="sp-stat-lbl">Impairment</div></div>'.format(n_imp),
            '<div class="sp-stat"><div class="sp-stat-num" style="color:#888">{}</div><div class="sp-stat-lbl">N/A</div></div>'.format(n_na),
            '</div>',
            ('<div style="background:#f9f9f9;padding:8px 12px;border-radius:6px;font-size:12px;margin-top:8px"><b>Notes:</b> {}</div>'.format(sp_pdata.get('notes','')) if sp_pdata.get('notes') else ''),
            '</div>',

            # Deficiencies
            '<div class="rpt-section">',
            '<div class="rpt-section-title">⚠️ Deficiencies & Non-Conformances</div>',
            def_html,
            '</div>',

            # Full items table
            '<div class="rpt-section">',
            '<div class="rpt-section-title">Inspection Items</div>',
            '<table class="rpt-table"><thead><tr>',
            '<th>System</th><th>Component</th><th>Location</th><th>Procedure</th>',
            '<th>Criteria</th><th>Status</th><th>Reading</th><th>Comments</th>',
            '</tr></thead><tbody>', items_rows, '</tbody></table>',
            '</div>',

            # Field Photos
            '<div class="rpt-section">',
            '<div class="rpt-section-title">📷 Field Photos</div>',
        ]

        # Load photos for SP inspection
        try:
            _sp_insp_id = sp_pdata.get('insp_id')
            if _sp_insp_id:
                _sb_client = db.get_supabase_client() if hasattr(db, 'get_supabase_client') else None
                _sp_photos = []
                if _sb_client:
                    _spr = _sb_client.table('inspection_photos').select('*').eq('inspection_type', 'sp').eq('inspection_id', _sp_insp_id).execute()
                    _sp_photos = _spr.data if _spr and _spr.data else []
                if _sp_photos:
                    html_parts.append('<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">')
                    for _ph in _sp_photos:
                        html_parts.append(
                            '<div style="border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">'
                            '<img src="{}" style="width:100%;max-height:200px;object-fit:cover">'.format(_ph.get('photo_data',''))
                            + '<div style="padding:6px 8px;font-size:11px;color:#555">'
                            '<b>{}</b> {}'.format(_ph.get('device_type',''), _ph.get('description',''))
                            + '<br><span style="color:#888">{}</span></div></div>'.format(
                                _ph.get('captured_at','')[:16] if _ph.get('captured_at') else ''))
                    html_parts.append('</div>')
                else:
                    html_parts.append('<p style="color:#888;font-style:italic;font-size:12px">No field photos attached.</p>')
            else:
                html_parts.append('<p style="color:#888;font-style:italic;font-size:12px">No field photos attached.</p>')
        except Exception as _pe:
            html_parts.append(f'<p style="color:#888;font-style:italic;font-size:12px">Photos not available</p>')

        html_parts.append('</div>')

        # Signature
        html_parts.append('<div class="rpt-section">')
        html_parts.append('<div class="rpt-section-title">Certification</div>')
        html_parts.append('<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:24px;margin-top:8px">')
        html_parts.append('<div><div class="rpt-label">Inspector Signature</div><div class="sig-line"></div><div style="font-size:11px;color:#888">{}</div></div>'.format(sp_pdata.get('inspector','—')))
        html_parts.append('<div><div class="rpt-label">Date</div><div class="sig-line"></div><div style="font-size:11px;color:#888">{}</div></div>'.format(sp_pdata.get('date','—')))
        html_parts.append('<div><div class="rpt-label">Reviewed By</div><div class="sig-line"></div><div style="font-size:11px;color:#888">&nbsp;</div></div>')
        html_parts.append('</div></div>')
        html_parts.append('</div>')  # end print-page

        st.markdown(''.join(html_parts), unsafe_allow_html=True)

        # Buttons
        st.divider()
        pc1, pc2 = st.columns(2)
        with pc1:
            import streamlit.components.v1 as _components
            _components.html("""<button onclick="window.parent.print()" style="
                background:#0369a1;color:white;border:none;padding:10px 20px;
                border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;
                width:100%;font-family:sans-serif">🖨️ Print / Save PDF</button>""", height=50)
        with pc2:
            if st.button("← Back to SP History", use_container_width=True):
                del st.session_state['sp_print_data']
                st.session_state['nav_target'] = '📁  SP Inspection History'
                st.rerun()
        st.stop()

    # ── Fire Alarm inspection print ───────────────────────────────────────────
    rdata = st.session_state.get('print_report_data')

    if not rdata:
        st.info("No report loaded. Open a saved report from **Inspection History** → 🖨️ Print Report, or fill out a New Inspection and click Preview & Print.")
        if st.button("← Go to Inspection History"):
            st.session_state['nav_target'] = '📁  Inspection History'
            st.rerun()
        st.stop()

    b      = rdata.get('bldg') or {}
    if not b:
        st.error("Report data missing building info. Please reload the inspection.")
        if st.button("← Back"):
            st.session_state['nav_target'] = '📁  Inspection History'
            st.rerun()
        st.stop()
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
    img_b64, img_ext = dbm.get_building_image(b.get('bldg_num',''))
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

        # Field Photos
        '<div class="rpt-section">',
        '<div class="rpt-section-title">📷 Field Photos</div>',
    ]

    # Load photos from inspection_photos table
    try:
        _insp_id = rdata.get('_insp_id') or rdata.get('insp_id')
        if _insp_id:
            _sb = db.get_supabase_client() if hasattr(db, 'get_supabase_client') else None
            _photos = []
            if _sb:
                _pr = _sb.table('inspection_photos').select('*').eq('inspection_type', 'fa').eq('inspection_id', _insp_id).execute()
                _photos = _pr.data if _pr and _pr.data else []
            if _photos:
                html_parts.append('<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">')
                for _ph in _photos:
                    html_parts.append(
                        '<div style="border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">'
                        '<img src="{}" style="width:100%;max-height:200px;object-fit:cover">'.format(_ph.get('photo_data',''))
                        + '<div style="padding:6px 8px;font-size:11px;color:#555">'
                        '<b>{}</b> {}'.format(_ph.get('device_type',''), _ph.get('description',''))
                        + '<br><span style="color:#888">{}</span></div></div>'.format(
                            _ph.get('captured_at','')[:16] if _ph.get('captured_at') else ''))
                html_parts.append('</div>')
            else:
                html_parts.append('<p style="color:#888;font-style:italic;font-size:12px">No field photos attached.</p>')
        else:
            html_parts.append('<p style="color:#888;font-style:italic;font-size:12px">No field photos attached.</p>')
    except Exception as _pe:
        html_parts.append(f'<p style="color:#888;font-style:italic;font-size:12px">Photos not available</p>')

    html_parts.append('</div>')

    # Notes
    html_parts.append('<div class="rpt-section">')
    html_parts.append('<div class="rpt-section-title">Notes &amp; Summary</div>')
    html_parts.append('<p style="font-size:12px;color:#444;line-height:1.6">{}</p>'.format(rdata.get('notes','') or 'No additional notes.'))
    html_parts.append('<p style="font-size:11px;color:#888;margin-top:10px;font-style:italic">The fire alarm system has been tested in accordance with NFPA 72 (2016), IFC 2018, and Utah Fire Code R7-10.</p>')
    html_parts.append('</div>')

    # Signatures
    html_parts.append('<div class="rpt-section">')
    html_parts.append('<div class="rpt-section-title">Signatures</div>')
    html_parts.append('<div style="display:grid;grid-template-columns:1fr 1fr;gap:32px;margin-top:12px">')
    html_parts.append('<div><div class="sig-line"></div><div style="font-size:11px;color:#888">Inspector Signature &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Date</div></div>')
    html_parts.append('<div><div class="sig-line"></div><div style="font-size:11px;color:#888">Print Name &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Certification #</div></div>')
    html_parts.append('</div></div>')
    html_parts.append('</div>')  # /print-page

    st.markdown('\n'.join(html_parts), unsafe_allow_html=True)

    st.divider()
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        import streamlit.components.v1 as _components
        _components.html("""
        <button onclick="window.parent.print()" style="
            background:#CC2929;color:white;border:none;padding:10px 20px;
            border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;width:100%;
            font-family:sans-serif">
            🖨️ Print / Save PDF
        </button>""", height=50)
    with c2:
        if st.button("← Back to History", use_container_width=True):
            st.session_state['nav_target'] = '📁  Inspection History'
            st.rerun()
    with c3:
        st.caption("💡 In print dialog: set **Margins → None**, enable **Background graphics** for best results.")

