from db_config import using_supabase

def delete_inspection(insp_id):
    if not using_supabase():
        import db
        return db.delete_inspection(insp_id)
    print("Supabase delete placeholder")
