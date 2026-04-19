#!/usr/bin/env -S uv run --with=requests --env-file=.env python3

import os
import sys
import json
from datetime import datetime
import time
import argparse

try:
    import requests
except ImportError:
    print("Installing requests...", file=sys.stderr)
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "requests"])
    import requests

VERCEL_TOKEN = os.environ.get("VERCEL_TOKEN")
VERCEL_PROJECT_ID = os.environ.get("VERCEL_PROJECT_ID")

if not VERCEL_TOKEN or not VERCEL_PROJECT_ID:
    print("ERROR: VERCEL_TOKEN or VERCEL_PROJECT_ID not found", file=sys.stderr)
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {VERCEL_TOKEN}",
    "Content-Type": "application/json"
}

def list_all_deployments():
    """List all deployments for the project."""
    deployments = []
    url = f"https://api.vercel.com/v6/deployments?projectId={VERCEL_PROJECT_ID}&limit=100"

    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        deployments.extend(data.get("deployments", []))

        pagination = data.get("pagination", {})
        if pagination.get("next"):
            url = f"https://api.vercel.com/v6/deployments?projectId={VERCEL_PROJECT_ID}&limit=100&until={pagination['next']}"
        else:
            url = None

    return deployments

def delete_deployment(deployment_id, deployment_name):
    """Delete a deployment by ID."""
    url = f"https://api.vercel.com/v13/deployments/{deployment_id}"
    response = requests.delete(url, headers=headers)

    if response.status_code == 200:
        print(f"✓ Deleted: {deployment_name} ({deployment_id})")
        return True
    elif response.status_code == 429:
        data = response.json()
        reset_time = data.get("error", {}).get("limit", {}).get("reset")
        if reset_time:
            reset_dt = datetime.fromtimestamp(reset_time)
            print(f"⚠️  Rate limited. Reset at {reset_dt.strftime('%H:%M:%S')}", file=sys.stderr)
        return False
    else:
        print(f"✗ Failed to delete {deployment_name}: {response.status_code} - {response.text}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Clean up Vercel deployments, keeping only the most recent main Production deployment."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )

    args = parser.parse_args()

    print("Fetching all deployments...\n")
    deployments = list_all_deployments()

    print(f"Found {len(deployments)} total deployments\n")

    main_production_deployments = [
        d for d in deployments
        if d.get("target") == "production" and d.get("meta", {}).get("githubCommitRef") == "main"
    ]

    if not main_production_deployments:
        print("ERROR: No main Production deployment found!", file=sys.stderr)
        sys.exit(1)

    main_production_deployments.sort(key=lambda d: d.get("created", 0), reverse=True)
    keep_deployment = main_production_deployments[0]

    keep_id = keep_deployment["uid"]
    keep_url = keep_deployment.get("url", "N/A")
    keep_created = datetime.fromtimestamp(keep_deployment["created"] / 1000).strftime("%Y-%m-%d %H:%M:%S")

    print(f"KEEPING most recent main Production deployment:")
    print(f"  ID: {keep_id}")
    print(f"  URL: {keep_url}")
    print(f"  Created: {keep_created}")
    print(f"  Commit: {keep_deployment.get('meta', {}).get('githubCommitSha', 'N/A')[:7]}")
    print()

    to_delete = [d for d in deployments if d["uid"] != keep_id]

    print(f"Will delete {len(to_delete)} deployments\n")

    if not to_delete:
        print("Nothing to delete!")
        return

    if args.dry_run:
        print("DRY RUN - would delete:")
        for d in to_delete[:10]:
            ref = d.get('meta', {}).get('githubCommitRef', 'unknown')
            url = d.get('url', 'N/A')
            print(f"  - {ref} - {url}")
        if len(to_delete) > 10:
            print(f"  ... and {len(to_delete) - 10} more")
        return

    print("Deleting deployments...")
    deleted_count = 0
    failed_count = 0
    has_waited_for_rate_limit = False

    for i, deployment in enumerate(to_delete, 1):
        deployment_id = deployment["uid"]
        deployment_info = f"{deployment.get('meta', {}).get('githubCommitRef', 'unknown')} - {deployment.get('url', 'N/A')}"

        result = delete_deployment(deployment_id, deployment_info)
        if result:
            deleted_count += 1
        else:
            failed_count += 1
            if failed_count > 50 and i < len(to_delete):
                if has_waited_for_rate_limit:
                    remaining = len(to_delete) - deleted_count
                    print(f"\nERROR: Hit rate limit again after waiting. Aborting.", file=sys.stderr)
                    print(f"Stats: total={len(to_delete)}, deleted={deleted_count}, remaining={remaining}", file=sys.stderr)
                    sys.exit(1)

                print(f"\nRate limited after {i} deletions. Waiting 7 minutes...")
                time.sleep(420)
                print("Resuming deletions...\n")
                failed_count = 0
                has_waited_for_rate_limit = True

        if i % 25 == 0:
            print(f"Progress: {i}/{len(to_delete)} deletions attempted...")

        time.sleep(0.1)

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Deleted: {deleted_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Kept: 1 (most recent main Production)")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
