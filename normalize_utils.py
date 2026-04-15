import logging
from datetime import datetime

MONTHS_LIST = [
    'January','February','March','April','May','June',
    'July','August','September','October','November','December'
]

logger = logging.getLogger(__name__)


def normalize_bldg_num(value):
    if value is None:
        return None
    text = str(value).strip()
    if text == '' or text.lower() in {'nan', 'none', 'null'}:
        return None
    try:
        return str(int(float(text)))
    except (TypeError, ValueError):
        return text


def normalize_text(value):
    if value is None:
        return ''
    text = str(value).strip()
    if text.lower() in {'nan', 'none', 'null'}:
        return ''
    return text


def safe_int(value):
    text = normalize_text(value)
    if not text:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def safe_float(value):
    text = normalize_text(value)
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def normalize_date_text(value):
    text = normalize_text(value)
    if not text:
        return None
    upper = text.upper()
    if upper in {'NEW CONSTR', 'NEW CONSTRUCTION', 'CONSTRUCTION'}:
        return 'CONSTRUCTION'
    if len(text) >= 10:
        candidate = text[:10]
        try:
            datetime.fromisoformat(candidate)
            return candidate
        except ValueError:
            pass
    return text


def derive_schedule_status(month, completed, inspection_date):
    month_num = MONTHS_LIST.index(month) + 1 if month in MONTHS_LIST else 99
    cur_month = datetime.today().month
    completed_text = normalize_text(completed)
    normalized_date = normalize_date_text(inspection_date)

    if normalized_date == 'CONSTRUCTION':
        return 'Construction', None
    if completed_text in {'3', '3.0', 'yes', 'true', 'complete'}:
        return 'Complete', normalized_date
    if month_num < cur_month:
        return 'Overdue', normalized_date
    return 'Pending', normalized_date


def clean_building_record(raw):
    return {
        'bldg_num': normalize_bldg_num(raw.get('Bldg #') or raw.get('bldg_num')),
        'name': normalize_text(raw.get('Building Name') or raw.get('building_name') or raw.get('name')),
        'report_name': normalize_text(raw.get('Report Name') or raw.get('report_name')),
        'district': normalize_text(raw.get('District') or raw.get('district')),
        'address': normalize_text(raw.get('Street Address') or raw.get('address')),
        'city': normalize_text(raw.get('City') or raw.get('city')),
        'state': normalize_text(raw.get('State') or raw.get('state')),
        'zip': normalize_text(raw.get('Zip') or raw.get('zip')),
        'built': safe_int(raw.get('Built') or raw.get('built')),
        'sq_ft': safe_int(raw.get('Gross Sq Ft') or raw.get('sq_ft')),
        'aux': normalize_text(raw.get('Aux (Yes/No)') or raw.get('aux')),
        'panel_type': normalize_text(raw.get('Panel Type') or raw.get('panel_type')),
        'year_installed': safe_int(raw.get('Year Installed') or raw.get('year_installed')),
        'age': safe_int(raw.get('Age Of System') or raw.get('age')),
        'gateway': normalize_text(raw.get('Gateway  (Yes/No)') or raw.get('gateway')),
        'inspection_month': normalize_text(raw.get('Inspection Month') or raw.get('inspection_month')),
        'scheduled_date': normalize_date_text(raw.get('Inspection Date') or raw.get('scheduled_date')),
        'replacement_priority': safe_int(raw.get('Critical Replacement (1-5, 5 Being Most Critical)') or raw.get('replacement_priority')),
        'replacement_cost': safe_float(raw.get('Replacement Cost') or raw.get('replacement_cost')),
        'replacement_scheduled': normalize_text(raw.get('Replacement Scheduled (Yes/No/Na)') or raw.get('replacement_scheduled')),
        'gateway_ip': normalize_text(raw.get('Gateway Ip Addresses') or raw.get('gateway_ip')),
        'anx_ip': normalize_text(raw.get('Anx Ip Addresses') or raw.get('anx_ip')),
        'subnet': normalize_text(raw.get('Subnet') or raw.get('subnet')),
        'vlan': normalize_text(raw.get('Vlan') or raw.get('vlan')),
        'nodes': safe_int(raw.get('Nodes') or raw.get('nodes')),
        'transponders': safe_int(raw.get('Transponders') or raw.get('transponders')),
        'smoke': safe_int(raw.get('Smoke Detectors') or raw.get('smoke')),
        'heat': safe_int(raw.get('Heat Detectors') or raw.get('heat')),
        'pull': safe_int(raw.get('Pull Stations') or raw.get('pull')),
        'duct': safe_int(raw.get('Duct Dectors') or raw.get('duct')),
        'init_devices': safe_int(raw.get('Intitiation Devices') or raw.get('init_devices')),
        'notif_devices': safe_float(raw.get('Notification Devices') or raw.get('notif_devices')),
        'panel_location': normalize_text(raw.get('Panel Location') or raw.get('panel_location')),
        'focalpoint_name': normalize_text(raw.get('FocalPoint Name') or raw.get('focalpoint_name')),
        'time_to_test': safe_int(raw.get('Time To Test') or raw.get('time_to_test')),
        'aim_asset': normalize_text(raw.get('Aim Asset Number') or raw.get('aim_asset')),
    }


def clean_schedule_record(raw):
    status, inspection_date = derive_schedule_status(
        normalize_text(raw.get('month')),
        raw.get('completed'),
        raw.get('inspection_date'),
    )
    return {
        'month': normalize_text(raw.get('month')),
        'bldg_num': normalize_bldg_num(raw.get('bldg_num')),
        'building_name': normalize_text(raw.get('building_name')),
        'district': normalize_text(raw.get('district')),
        'address': normalize_text(raw.get('address')),
        'est_hours': safe_float(raw.get('est_hours')),
        'inspection_date': inspection_date,
        'status': status,
        'date_completed': None,
        'uploaded_cms': 'Yes' if str(raw.get('uploaded_cms')).strip() in {'1', '1.0', 'Yes', 'yes', 'true', 'True'} else 'No',
        'notes': normalize_text(raw.get('notes')),
    }


def clean_device_record(raw):
    if raw is None:
        return None

    if isinstance(raw, dict):
        building = normalize_text(raw.get('building') or raw.get('Building') or raw.get('bldg') or raw.get('bldg_num'))
        point = normalize_text(raw.get('point') or raw.get('Point'))
        if not building or not point:
            return None
        return {
            'building': building,
            'type': normalize_text(raw.get('type') or raw.get('Type') or raw.get('device_type')),
            'point': point,
            'description': normalize_text(raw.get('description') or raw.get('Description')),
        }

    if isinstance(raw, (list, tuple)):
        if len(raw) < 3:
            return None
        return {
            'building': normalize_text(raw[0]),
            'type': normalize_text(raw[1]),
            'point': normalize_text(raw[2]),
            'description': normalize_text(raw[3] if len(raw) > 3 else ''),
        }

    return None


def clean_seed_payload(buildings, schedule, devices):
    cleaned_buildings = []
    for raw in buildings:
        row = clean_building_record(raw)
        if row['bldg_num']:
            cleaned_buildings.append(row)
        else:
            logger.warning('Skipping building with missing bldg_num: %s', raw)

    cleaned_schedule = []
    for raw in schedule:
        row = clean_schedule_record(raw)
        if row['bldg_num']:
            cleaned_schedule.append(row)
        else:
            logger.warning('Skipping schedule row with missing bldg_num: %s', raw)

    cleaned_devices = []
    for raw in devices:
        row = clean_device_record(raw)
        if row:
            cleaned_devices.append(row)
        else:
            logger.warning('Skipping malformed device row: %s', raw)

    return cleaned_buildings, cleaned_schedule, cleaned_devices
