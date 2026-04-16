
def search_sprinkler_inventory(bldg_num=None, floor=None, system_type=None, component=None, search=None):
    """Flexible inventory search. All filters optional."""
    if not _use_supabase(): return pd.DataFrame()
    try:
        q = _sb().table("sprinkler_inventory").select("*")
        if bldg_num and bldg_num != 'All':
            q = q.eq("bldg_num", str(bldg_num))
        if floor and floor != 'All':
            q = q.eq("floor", floor)
        if system_type and system_type != 'All':
            q = q.eq("system_type", system_type)
        if component and component != 'All':
            q = q.eq("component", component)
        data = q.order("bldg_num").order("floor").order("system_type").order("component").limit(2000).execute().data or []
        # Free-text search across all fields
        if search:
            s = search.lower()
            data = [r for r in data if any(s in str(v).lower() for v in r.values())]
        return pd.DataFrame(data) if data else pd.DataFrame(
            columns=['bldg_num','floor','room','system_type','component','address'])
    except Exception as e:
        print("search_sprinkler_inventory error:", e)
        return pd.DataFrame()

def get_inventory_filter_options():
    """Return distinct values for each filter dropdown."""
    if not _use_supabase():
        return {}, {}, {}, {}
    try:
        import streamlit as st
        @st.cache_data(ttl=300)
        def _load():
            sb = _sb()
            all_data = sb.table("sprinkler_inventory").select("bldg_num,floor,system_type,component").execute().data or []
            bldgs   = sorted(set(str(r['bldg_num']) for r in all_data if r.get('bldg_num')),
                             key=lambda x: (0, int(float(x))) if x.replace('.','').isdigit() else (1, x))
            floors  = sorted(set(r['floor'] for r in all_data if r.get('floor')))
            systems = sorted(set(r['system_type'] for r in all_data if r.get('system_type')))
            comps   = sorted(set(r['component'] for r in all_data if r.get('component')))
            return bldgs, floors, systems, comps
        return _load()
    except Exception as e:
        print("get_inventory_filter_options error:", e)
        return [], [], [], []
