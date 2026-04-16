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
        sp1 = (sb.table("master_buildings").select("bldg_num,sp_Actuator,sp_AirCompressor,sp_AirCompressorGauge,sp_AirDryer,sp_AirMaintenanceDevice,sp_AirReleaseValve,sp_AirTank,sp_AlarmBell,sp_AlarmLineValve,sp_AlarmTestValve,sp_AlarmValve,sp_AutomaticDrainValve,sp_AuxiliaryDrain,sp_AuxiliaryDrainValve,sp_AuxliaryDrain,sp_Backflow,sp_BallDrip,sp_BallDripFDC,sp_BallValve,sp_CheckValve,sp_CheckValveFDC,sp_CondensateDrainValve,sp_ContolValve,sp_Control,sp_ControlValve,sp_ControlValveOS_Y,sp_ControlValvePIV,sp_ControlValvePRV,sp_DrainDischarge,sp_DripDrum,sp_DryPipeValve,sp_ExpansionTank,sp_FDC,sp_FirePumpController,sp_FlowMeter,sp_HighAirSwitch,sp_HoseValve,sp_HydraulicDesignSign,sp_HydraulicDesignSign5,sp_HydraulicDesignSign6,sp_HydraulicDesignSign7,sp_HydraulicDesignSign8,sp_InspectorsTest,sp_InstallationDrawings,sp_JockeyPumpController,sp_L1M002,sp_LowAirSwitch")
               .eq("bldg_num", bn).limit(1).execute().data or [{}])[0]
        sp2 = (sb.table("master_buildings").select("bldg_num,sp_MainDrainDischarge,sp_MainDrainValve,sp_MainFeed,sp_ManualEmergencyStation,sp_MasterPressureRegulatingDevice,sp_MechanicalBell,sp_MMTS,sp_MMWF,sp_MonitorModule,sp_MonitorModule_Solenoid_,sp_MonitorModuleHA,sp_MonitorModuleLA,sp_MonitorModulePIV,sp_MonitorModulePS,sp_MonitorModuleSolenoid,sp_MonitorModuleTS,sp_MonitorModuleWF,sp_MonitorModuleWFAT,sp_MonitorMonduleLA,sp_NitrogenExhaustManifold,sp_NitrogenGenerator,sp_NitrogenInjectionManifold,sp_NitrogenInjectionPort,sp_NitrogenTank,sp_PreactionValve,sp_PressureSwitch,sp_Pump,sp_PurgeValve,sp_PushrodChamberSupplyValve,sp_ReliefValve,sp_ResetKnob,sp_RetardingChamber,sp_Riser,sp_RoofManifold,sp_Solenoid,sp_SprinklerBox,sp_Strainer,sp_SupplyGauge,sp_SystemGauge,sp_SystemRiser,sp_TamperSwitch,sp_TestHeader,sp_TransferSwitch,sp_Waterflow,sp_WaterflowTestKey,sp_WaterflowTestPump,sp_WaterTank")
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
    def _safe(name): return 'sp_' + _re.sub(r'[^a-zA-Z0-9_]', '_', name)
    return {c: int(b.get(_safe(c)) or 0) for c in SP_COMPONENTS
            if int(b.get(_safe(c)) or 0) > 0}
