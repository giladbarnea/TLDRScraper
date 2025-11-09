### 4. Enable Row Level Security (RLS)

**THIS IS MANDATORY BEFORE ANY DATA ACCESS WORKS.**

Even on free tier, Supabase enforces security through RLS. Here's what happens:

**Without RLS:**
- Anyone with your `anon` key can read/write all data
- Terrible security, but works for testing

**With RLS enabled but no policies:**
- **ALL ACCESS IS BLOCKED** (including your own API calls)
- You'll get empty results or `403 Forbidden` errors

**With RLS enabled + policies:**
- Access controlled per row based on policies
- Secure, production-ready

**How to enable RLS:**

Via Dashboard:
1. Go to `Database > Tables`
2. Click on table name
3. Click "Enable RLS" in top right

Via SQL:
```sql
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
```

**Then create policies** (see [Security: RLS Configuration](#security-rls-configuration) section below).

### 5. Verify Setup

Test connection with Python:

```python
from supabase import create_client
import os

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

# Test query (replace 'test_table' with your table name)
try:
    result = supabase.table('test_table').select('*').limit(1).execute()
    print("✓ Connection successful:", result.data)
except Exception as e:
    print("✗ Connection failed:", e)
```

**Common errors:**
- `"relation \"test_table\" does not exist"`: Table not created yet
- `"Failed to fetch"`: Wrong SUPABASE_URL
- `"Invalid API key"`: Wrong SUPABASE_SERVICE_KEY
- Empty results but no error: RLS enabled with no policies (using anon key)