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
        @st.cache_data(ttl=300)
        def _load():
            sb = _sb()
            all_rows, offset = [], 0
            while True:
                batch = (sb.table("master_buildings").select("*")
                         .order("bldg_num").range(offset, offset+999).execute().data or [])
                all_rows.extend(batch)
                if len(batch) < 1000: break
                offset += 1000
            return all_rows
        return _load()
    except Exception as e:
        print("get_master_buildings error:", e); return []

def get_master_building(bldg_num):
    if not _use_supabase(): return {}
    try:
        res = (_sb().table("master_buildings").select("*")
               .eq("bldg_num", str(bldg_num)).limit(1).execute())
        return (res.data or [{}])[0]
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
    return {c: int(b.get(f'sp_{c}') or 0) for c in SP_COMPONENTS
            if int(b.get(f'sp_{c}') or 0) > 0}
