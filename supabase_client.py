from supabase import create_client
import util
import ssl

_original_create_default_context = ssl.create_default_context

def _create_unverified_context(*args, **kwargs):
    context = _original_create_default_context(*args, **kwargs)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context

ssl.create_default_context = _create_unverified_context

_supabase_client = None

def get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        url = util.resolve_env_var("SUPABASE_URL")
        key = util.resolve_env_var("SUPABASE_SERVICE_KEY")
        _supabase_client = create_client(url, key)
    return _supabase_client
