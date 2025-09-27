import os
import time
from edge_config import set_json, get_json


def main():
    ec = os.environ.get("EDGE_CONFIG")
    ec_id = os.environ.get("EDGE_CONFIG_ID")
    token = os.environ.get("VERCEL_TOKEN")
    print(f"EDGE_CONFIG present={bool(ec)} id_present={bool(ec_id)} token_present={bool(token)} id={ec_id}")

    ts = int(time.time())
    key = f"tldr-cache-test-{ts}"
    value = {
        "status": "hit",
        "date": "1970-01-01",
        "newsletter_type": "test",
        "articles": []
    }
    ok = set_json(key, value)
    print(f"WRITE ok={ok} key={key}")
    got = get_json(key)
    print(f"READ value={got}")


if __name__ == "__main__":
    main()

