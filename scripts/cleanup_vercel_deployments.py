#!/usr/bin/env python3
"""
Delete all Vercel deployments except the current production deployment.

This script uses the Vercel REST API to clean up old preview and production
deployments, keeping only the currently promoted production deployment.

Usage:
    python scripts/cleanup_vercel_deployments.py [--dry-run]

Environment variables required:
    VERCEL_TOKEN: Vercel authentication token
    VERCEL_PROJECT_ID: Vercel project ID

Example:
    # Dry run (shows what would be deleted)
    python scripts/cleanup_vercel_deployments.py --dry-run

    # Actually delete deployments
    python scripts/cleanup_vercel_deployments.py
"""

import os
import sys
import time
import argparse
import requests


def get_env_var(name):
    """Get required environment variable."""
    value = os.environ.get(name)
    if not value:
        print(f"Error: {name} environment variable not set", file=sys.stderr)
        sys.exit(1)
    return value


def fetch_all_deployments(token, project_id):
    """Fetch all deployments for a project."""
    api_base = "https://api.vercel.com"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    deployments = []
    url = f"{api_base}/v6/deployments?projectId={project_id}&limit=100"

    print("Fetching deployments from Vercel API...")
    page = 1

    while url:
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            page_deployments = data.get("deployments", [])
            deployments.extend(page_deployments)
            print(f"  Fetched page {page}: {len(page_deployments)} deployments")

            pagination = data.get("pagination", {})
            if pagination.get("next"):
                url = f"{api_base}/v6/deployments?projectId={project_id}&limit=100&until={pagination['next']}"
                page += 1
            else:
                url = None

        except requests.RequestException as e:
            print(f"Error fetching deployments: {e}", file=sys.stderr)
            sys.exit(1)

    return deployments


def find_production_deployment(deployments):
    """Find the currently promoted production deployment."""
    for dep in deployments:
        if dep.get("readySubstate") == "PROMOTED" and dep.get("target") == "production":
            return dep
    return None


def format_timestamp(timestamp_ms):
    """Format Unix timestamp (ms) to readable string."""
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp_ms / 1000))


def delete_deployment(token, deployment_id, dry_run=False):
    """Delete a deployment by ID."""
    if dry_run:
        return True

    api_base = "https://api.vercel.com"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        delete_url = f"{api_base}/v13/deployments/{deployment_id}"
        response = requests.delete(delete_url, headers=headers, timeout=30)
        return response.status_code in (200, 204)
    except requests.RequestException:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Delete all Vercel deployments except the current production deployment"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    args = parser.parse_args()

    token = get_env_var("VERCEL_TOKEN")
    project_id = get_env_var("VERCEL_PROJECT_ID")

    if args.dry_run:
        print("🔍 DRY RUN MODE - No deployments will be deleted\n")

    all_deployments = fetch_all_deployments(token, project_id)
    print(f"\nFound {len(all_deployments)} total deployments\n")

    production = find_production_deployment(all_deployments)

    if not production:
        print("❌ Error: Could not find promoted production deployment!", file=sys.stderr)
        sys.exit(1)

    print("✅ Current production deployment:")
    print(f"   ID:      {production['uid']}")
    print(f"   URL:     https://{production['url']}")
    print(f"   Created: {format_timestamp(production['created'])}")
    print()

    to_delete = [
        dep for dep in all_deployments
        if dep["uid"] != production["uid"]
    ]

    if not to_delete:
        print("✨ No deployments to delete - only production exists!")
        return

    print(f"📋 Will {'simulate deleting' if args.dry_run else 'delete'} {len(to_delete)} deployment(s)\n")

    deleted = 0
    failed = 0

    for dep in to_delete:
        dep_id = dep["uid"]
        dep_url = dep.get("url", "unknown")
        dep_target = dep.get("target") or "preview"
        dep_created = format_timestamp(dep.get("created", 0))

        prefix = "🔍 [DRY-RUN]" if args.dry_run else "🗑️ "
        print(f"{prefix} Deleting [{dep_target}] {dep_created}: {dep_url[:50]}... ", end="", flush=True)

        if delete_deployment(token, dep_id, dry_run=args.dry_run):
            print("✅")
            deleted += 1
        else:
            print("❌")
            failed += 1

        time.sleep(0.1)

    print()
    print("=" * 70)
    print("Summary:")
    print(f"  Total deployments:     {len(all_deployments)}")
    print(f"  {'Would delete' if args.dry_run else 'Deleted'}:            {deleted}")
    print(f"  Kept (production):     1")
    if failed > 0:
        print(f"  Failed:                {failed}")
    print("=" * 70)

    if args.dry_run:
        print("\n💡 Run without --dry-run to actually delete these deployments")


if __name__ == "__main__":
    main()
