from supabase import create_client
import util
import ssl
import httpx
import warnings

# Suppress SSL warnings when verification is disabled
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

_original_create_default_context = ssl.create_default_context

def _create_unverified_context(*args, **kwargs):
    context = _original_create_default_context(*args, **kwargs)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context

ssl.create_default_context = _create_unverified_context

# Monkey-patch httpx to disable SSL verification globally
_original_httpx_client = httpx.Client
_original_httpx_async_client = httpx.AsyncClient

def _patched_httpx_client(*args, **kwargs):
    kwargs['verify'] = False
    return _original_httpx_client(*args, **kwargs)

def _patched_httpx_async_client(*args, **kwargs):
    kwargs['verify'] = False
    return _original_httpx_async_client(*args, **kwargs)

httpx.Client = _patched_httpx_client
httpx.AsyncClient = _patched_httpx_async_client

_supabase_client = None

def get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        url = util.resolve_env_var("SUPABASE_URL")
        key = util.resolve_env_var("SUPABASE_SERVICE_KEY")
        _supabase_client = create_client(url, key)
    return _supabase_client