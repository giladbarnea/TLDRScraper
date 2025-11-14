from supabase import create_client
import util

_supabase_client = None

def get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        url = util.resolve_env_var("SUPABASE_URL")
        key = util.resolve_env_var("SUPABASE_SERVICE_KEY")
        _supabase_client = create_client(url, key)
    return _supabase_client