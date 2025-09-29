// scripts/blob_put.mjs
import { put } from '@vercel/blob';

async function main() {
  const {
    BLOB_READ_WRITE_TOKEN,
    PATHNAME,           // required: full pathname to write to
    CONTENT_TYPE = 'text/markdown; charset=utf-8',
    CACHE_MAX_AGE = '86400', // 1 day
    ALLOW_OVERWRITE = 'true',
  } = process.env;

  if (!BLOB_READ_WRITE_TOKEN) {
    console.error('BLOB_READ_WRITE_TOKEN is required');
    process.exit(2);
  }
  if (!PATHNAME) {
    console.error('PATHNAME env is required');
    process.exit(2);
  }

  // Read stdin as the Markdown payload
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  const body = Buffer.concat(chunks);

  const blob = await put(PATHNAME, body, {
    access: 'public',
    token: BLOB_READ_WRITE_TOKEN,
    contentType: CONTENT_TYPE,
    cacheControlMaxAge: Number(CACHE_MAX_AGE),
    addRandomSuffix: false,                       // important: deterministic
    allowOverwrite: ALLOW_OVERWRITE === 'true',   // opt-in overwrite
  });

  // Print a single-line JSON to stdout for easy parsing in Python
  process.stdout.write(JSON.stringify(blob));
}

main().catch((err) => {
  console.error(err?.stack || String(err));
  process.exit(1);
});
