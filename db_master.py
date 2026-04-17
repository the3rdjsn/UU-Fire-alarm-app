"""
db_master.py — Unified buildings data from master_buildings table.
Combines fire alarm + sprinkler info in one place.
"""
import os
import pandas as pd

SP_COMPONENTS = [
    "Actuator","AirCompressor","AirCompressorGauge","AirDryer","AirMaintenanceDevice",
    "AirReleaseValve","AirTank","AlarmBell","AlarmLineValve","AlarmTestValve","AlarmValve",
    "AutomaticDrainValve","AuxiliaryDrain","AuxiliaryDrainValve","AuxliaryDrain","Backflow",
    "BallDrip","BallDripFDC","BallValve","CheckValve","CheckValveFDC","CondensateDrainValve",
    "ContolValve","Control","ControlValve","ControlValveOS&Y","ControlValvePIV","ControlValvePRV",
    "DrainDischarge","DripDrum","DryPipeValve","ExpansionTank","FDC","FirePumpController",
    "FlowMeter","HighAirSwitch","HoseValve","HydraulicDesignSign","HydraulicDesignSign5",
    "HydraulicDesignSign6","HydraulicDesignSign7","HydraulicDesignSign8","InspectorsTest",
    "InstallationDrawings","JockeyPumpController","L1M002","LowAirSwitch","MainDrainDischarge",
    "MainDrainValve","MainFeed","ManualEmergencyStation","MasterPressureRegulatingDevice",
    "MechanicalBell","MMTS","MMWF","MonitorModule","MonitorModule(Solenoid)","MonitorModuleHA",
    "MonitorModuleLA","MonitorModulePIV","MonitorModulePS","MonitorModuleSolenoid",
    "MonitorModuleTS","MonitorModuleWF","MonitorModuleWFAT","MonitorMonduleLA",
    "NitrogenExhaustManifold","NitrogenGenerator","NitrogenInjectionManifold",
    "NitrogenInjectionPort","NitrogenTank","PreactionValve","PressureSwitch","Pump",
    "PurgeValve","PushrodChamberSupplyValve","ReliefValve","ResetKnob","RetardingChamber",
    "Riser","RoofManifold","Solenoid","SprinklerBox","Strainer","SupplyGauge","SystemGauge",
    "SystemRiser","TamperSwitch","TestHeader","TransferSwitch","Waterflow",
    "WaterflowTestKey","WaterflowTestPump","WaterTank"
]

def _use_supabase():
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"))

def _sb():
    from supabase import create_client
    import streamlit as st
    @st.cache_resource
    def _client():
        return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    return _client()

# ── Get all buildings ─────────────────────────────────────────────────────────

def get_master_buildings():
    if not _use_supabase(): return []
    try:
        import streamlit as st
        sb = _sb()
        # Simple test - just get bldg_num and name first
        test = sb.table("master_buildings").select("bldg_num,name").limit(5).execute()
        print(f"TEST QUERY: {len(test.data or [])} rows, data={test.data}")
        if not test.data:
            print("ERROR: master_buildings table appears empty or inaccessible")
            return []
        # Full fetch - base columns only first
        all_rows, offset = [], 0
        while True:
            batch = (sb.table("master_buildings")
                     .select("*")
                     .order("bldg_num")
                     .range(offset, offset+199)
                     .execute().data or [])
            all_rows.extend(batch)
            print(f"Fetched batch offset={offset}, got {len(batch)} rows, total={len(all_rows)}")
            if len(batch) < 200: break
            offset += 200
        return all_rows
    except Exception as e:
        import traceback
        print(f"get_master_buildings FULL ERROR: {e}")
        print(traceback.format_exc())
        return []


def get_master_building(bldg_num):
    if not _use_supabase(): return {}
    try:
        sb = _sb()
        bn = str(bldg_num)
        base = (sb.table("master_buildings").select("bldg_num,name,name_alarm,report_name,asset_name,dfcm_id,property_id,address,city,state,zip,responsibility,district,riser_folder,focalpoint_network,sq_ft,aux,aim_asset,panel_type,year_installed,age,gateway,inspection_month,gateway_ip,anx_ip,gateway_addr,subnet,vlan,amps,nodes,transponders,smoke,heat,pull,duct,notif_devices,init_devices,panel_location,focalpoint_name,total_sp_components,id,image_data,image_ext")
                .eq("bldg_num", bn).limit(1).execute().data or [{}])[0]
        if not base: return {}
        sp1 = (sb.table("master_buildings").select("bldg_num,sp_actuator,sp_aircompressor,sp_aircompressorgauge,sp_airdryer,sp_airmaintenancedevice,sp_airreleasevalve,sp_airtank,sp_alarmbell,sp_alarmlinevalve,sp_alarmtestvalve,sp_alarmvalve,sp_automaticdrainvalve,sp_auxiliarydrain,sp_auxiliarydrainvalve,sp_auxliarydrain,sp_backflow,sp_balldrip,sp_balldripfdc,sp_ballvalve,sp_checkvalve,sp_checkvalvefdc,sp_condensatedrainvalve,sp_contolvalve,sp_control,sp_controlvalve,sp_controlvalveos_y,sp_controlvalvepiv,sp_controlvalveprv,sp_draindischarge,sp_dripdrum,sp_drypipevalve,sp_expansiontank,sp_fdc,sp_firepumpcontroller,sp_flowmeter,sp_highairswitch,sp_hosevalve,sp_hydraulicdesignsign,sp_hydraulicdesignsign5,sp_hydraulicdesignsign6,sp_hydraulicdesignsign7,sp_hydraulicdesignsign8,sp_inspectorstest,sp_installationdrawings,sp_jockeypumpcontroller,sp_l1m002,sp_lowairswitch")
               .eq("bldg_num", bn).limit(1).execute().data or [{}])[0]
        sp2 = (sb.table("master_buildings").select("bldg_num,sp_maindraindischarge,sp_maindrainvalve,sp_mainfeed,sp_manualemergencystation,sp_masterpressureregulatingdevice,sp_mechanicalbell,sp_mmts,sp_mmwf,sp_monitormodule,sp_monitormodule_solenoid_,sp_monitormoduleha,sp_monitormodulela,sp_monitormodulepiv,sp_monitormoduleps,sp_monitormodulesolenoid,sp_monitormodulets,sp_monitormodulewf,sp_monitormodulewfat,sp_monitormondulela,sp_nitrogenexhaustmanifold,sp_nitrogengenerator,sp_nitrogeninjectionmanifold,sp_nitrogeninjectionport,sp_nitrogentank,sp_preactionvalve,sp_pressureswitch,sp_pump,sp_purgevalve,sp_pushrodchambersupplyvalve,sp_reliefvalve,sp_resetknob,sp_retardingchamber,sp_riser,sp_roofmanifold,sp_solenoid,sp_sprinklerbox,sp_strainer,sp_supplygauge,sp_systemgauge,sp_systemriser,sp_tamperswitch,sp_testheader,sp_transferswitch,sp_waterflow,sp_waterflowtestkey,sp_waterflowtestpump,sp_watertank")
               .eq("bldg_num", bn).limit(1).execute().data or [{}])[0]
        base.update(sp1)
        base.update(sp2)
        return base
    except Exception as e:
        print("get_master_building error:", e); return {}


def update_master_building(bldg_num, fields):
    if not _use_supabase(): return
    try:
        _sb().table("master_buildings").update(fields).eq("bldg_num", str(bldg_num)).execute()
    except Exception as e:
        print("update_master_building error:", e)

# ── Images (stored directly on master_buildings row) ─────────────────────────

def get_building_image(bldg_num):
    if not _use_supabase(): return None, None
    try:
        res = (_sb().table("master_buildings")
               .select("image_data,image_ext").eq("bldg_num", str(bldg_num)).limit(1).execute())
        row = (res.data or [{}])[0]
        return row.get("image_data"), row.get("image_ext")
    except Exception as e:
        print("get_building_image error:", e); return None, None

def save_building_image(bldg_num, image_bytes, ext='jpg'):
    import base64
    if not _use_supabase(): return
    try:
        b64 = base64.b64encode(image_bytes).decode()
        _sb().table("master_buildings").update({"image_data": b64, "image_ext": ext})\
            .eq("bldg_num", str(bldg_num)).execute()
    except Exception as e:
        print("save_building_image error:", e)

def delete_building_image(bldg_num):
    if not _use_supabase(): return
    try:
        _sb().table("master_buildings").update({"image_data": None, "image_ext": None})\
            .eq("bldg_num", str(bldg_num)).execute()
    except Exception as e:
        print("delete_building_image error:", e)

# ── Helpers ───────────────────────────────────────────────────────────────────

def sort_buildings(buildings):
    def _key(b):
        n = str(b.get('bldg_num',''))
        try: return (0, int(float(n)))
        except: return (1, n)
    return sorted(buildings, key=_key)

def building_label(b):
    name = b.get('name') or b.get('name_alarm') or ''
    return f"{b['bldg_num']} — {name}" if name else str(b['bldg_num'])

def get_sp_components(b):
    """Return dict of non-zero sprinkler component counts for a building."""
    import re as _re
    def _safe(name): return 'sp_' + _re.sub(r'[^a-zA-Z0-9_]', '_', name).lower()
    result = {}
    for c in SP_COMPONENTS:
        key = _safe(c)
        val = b.get(key) or b.get(key.replace('sp_','sp_').lower()) or 0
        try:
            v = int(float(val))
            if v > 0:
                result[c] = v
        except: pass
    return result

# ── Component Images ──────────────────────────────────────────────────────────

import os as _os
import re as _re

_REPO_BASE   = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)))
_IMAGES_BASE = _os.path.join(_REPO_BASE, "images", "Riser Inventory Pictures")

# Cache: bldg_num -> list of (normalized_key, filepath)
_img_cache = {}

def _normalize(s):
    """Lowercase, strip, collapse spaces, remove special chars for fuzzy compare."""
    if not s: return ''
    s = str(s).lower().strip()
    s = _re.sub(r'[^a-z0-9]', '', s)
    return s

def _score(needle_parts, candidate):
    """
    Score how well a candidate filename matches a set of normalized parts.
    Returns 0-100. Higher = better match.
    """
    cand = _normalize(candidate)
    hits = sum(1 for p in needle_parts if p and p in cand)
    return int(hits / len(needle_parts) * 100) if needle_parts else 0

def _build_cache(bldg_num, riser_folder):
    """Walk building image folder and cache all image paths."""
    key = (str(bldg_num), str(riser_folder))
    if key in _img_cache:
        return _img_cache[key]
    entries = []
    # Try exact riser_folder first, then walk all district folders if not found
    candidates = []
    if riser_folder:
        d = _os.path.join(_IMAGES_BASE, str(riser_folder), str(bldg_num))
        candidates.append(d)
    # Also try all district folders (handles wrong riser_folder)
    if _os.path.isdir(_IMAGES_BASE):
        for district in _os.listdir(_IMAGES_BASE):
            d2 = _os.path.join(_IMAGES_BASE, district, str(bldg_num))
            if d2 not in candidates:
                candidates.append(d2)
    for bldg_dir in candidates:
        if not _os.path.isdir(bldg_dir):
            continue
        for root, dirs, files in _os.walk(bldg_dir):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    full = _os.path.join(root, f)
                    entries.append((_normalize(f), full))
        if entries:
            break  # found images, stop searching
    _img_cache[key] = entries
    return entries

def get_component_image_path(bldg_num, floor, room, system_type, component, riser_folder):
    """
    Fuzzy match: find the best image for a component.
    Tries exact path first, falls back to scored fuzzy search across all
    images in the building folder.
    """
    if not bldg_num or not component:
        return None
    try:
        # 1. Try exact path first (fast path)
        folder_room = f"{floor} {room}".strip()
        filename    = f"{bldg_num} {floor} {room} {system_type} {component}.jpg"
        exact = _os.path.join(_IMAGES_BASE, str(riser_folder or ''),
                              str(bldg_num), folder_room, filename)
        if _os.path.exists(exact):
            return exact

        # 2. Fuzzy search across cached image list
        entries = _build_cache(bldg_num, riser_folder)
        if not entries:
            return None

        # Build needle from meaningful parts (skip empty/numeric-only tokens)
        needle_parts = [_normalize(p) for p in [floor, room, system_type, component] if p]
        # Component and system_type are highest priority
        priority     = [_normalize(p) for p in [component, system_type] if p]

        best_path  = None
        best_score = 0
        for norm_name, filepath in entries:
            # Must match component at minimum
            if not any(p in norm_name for p in priority[:1]):
                continue
            score = _score(needle_parts, norm_name)
            if score > best_score:
                best_score = score
                best_path  = filepath

        # Return if reasonably confident (>= 2 parts matched)
        return best_path if best_score >= 40 else None
    except Exception as e:
        print(f"get_component_image_path error: {e}")
        return None

def get_all_component_images(bldg_num, riser_folder):
    """Return list of all image paths for a building."""
    if not bldg_num:
        return []
    try:
        return [fp for _, fp in _build_cache(bldg_num, riser_folder)]
    except:
        return []

def get_component_images_fuzzy(bldg_num, riser_folder, component):
    """
    Return all images for a specific component across all locations in a building.
    Sorted by best match score descending.
    """
    if not bldg_num or not component:
        return []
    try:
        entries  = _build_cache(bldg_num, riser_folder)
        comp_key = _normalize(component)
        matches  = []
        for norm_name, filepath in entries:
            if comp_key in norm_name:
                # Extract floor/room from path for display
                parts = filepath.replace('\\', '/').split('/')
                loc   = parts[-2] if len(parts) >= 2 else ''
                matches.append((norm_name, filepath, loc))
        return [(fp, loc) for _, fp, loc in matches]
    except Exception as e:
        print(f"get_component_images_fuzzy error: {e}")
        return []

def clear_image_cache(bldg_num=None, riser_folder=None):
    """Clear cached image list (call after new images added)."""
    global _img_cache
    if bldg_num:
        key = (str(bldg_num), str(riser_folder or ''))
        _img_cache.pop(key, None)
    else:
        _img_cache = {}

# ── Add / Import Buildings ────────────────────────────────────────────────────

def add_building(fields: dict):
    """Insert a single new building. Returns inserted row or None."""
    if not _use_supabase(): return None
    try:
        res = _sb().table("master_buildings").insert(fields).execute()
        return (res.data or [None])[0]
    except Exception as e:
        print("add_building error:", e); return None

def import_buildings(rows: list):
    """Bulk insert list of building dicts. Returns (inserted_count, errors)."""
    if not _use_supabase(): return 0, []
    errors = []
    inserted = 0
    import re
    def safe_col(name):
        return 'sp_' + re.sub(r'[^a-zA-Z0-9_]', '_', name).lower()
    for i in range(0, len(rows), 50):
        batch = rows[i:i+50]
        try:
            _sb().table("master_buildings").upsert(batch, on_conflict="bldg_num").execute()
            inserted += len(batch)
        except Exception as e:
            errors.append(str(e))
    return inserted, errors
