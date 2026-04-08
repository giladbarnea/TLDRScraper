#!/usr/bin/env bash

# sync_subdir: Seamlessly mirrors a specific subdirectory from a remote repo into a local path.
# 
# Design rationale & Git workarounds:
# 1. Subdirectory Isolation: Basic `git subtree pull <url>` merges the remote's *root*. To map a
#    remote *subdirectory*, we must fetch the repo and isolate the folder into a synthetic branch 
#    using `git subtree split FETCH_HEAD` before adding/merging it locally.
# 2. Stateless: Fetches directly via URL to avoid polluting local `git remote` configuration.
# 3. The "Fake Dir" Hack: `git subtree split FETCH_HEAD` inexplicably fails if the target prefix 
#    doesn't exist on the *local* filesystem. We temporarily `mkdir` it to bypass this. This safely 
#    avoids dangerous `git checkout` commands inside a git hook, protecting uncommitted local changes.

# Helper function to sync a specific subdirectory from an external git repository
# into a specific local directory, using git subtree.

sync_subdir() {
    local repo_url="$1"
    shift
    
    local src_dir=""
    local dest_dir=""
    
    # Parse remaining arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --prefix=*)
                src_dir="${1#*=}"
                shift
                ;;
            --target=*)
                dest_dir="${1#*=}"
                shift
                ;;
            *)
                echo "Unknown argument: $1"
                return 1
                ;;
        esac
    done

    if [[ -z "$src_dir" || -z "$dest_dir" ]]; then
        echo "Usage: sync_subdir <repo_url> --prefix=<src_dir> --target=<dest_dir>"
        return 1
    fi
    
    echo "==> Syncing $src_dir from $repo_url to $dest_dir"
    
    # 1. Fetch the remote silently (no remote config needed!)
    git fetch "$repo_url" main --quiet
    
    # 2. Bypass git-subtree's filesystem check by ensuring the source path exists locally
    local created_fake_dir=false
    if [ ! -e "$src_dir" ]; then
        mkdir -p "$src_dir"
        created_fake_dir=true
    fi
    
    # 3. Extract the subdirectory from the fetched commit into a temp branch
    local tmp_branch="tmp-split-$RANDOM"
    git subtree split --prefix="$src_dir" -b "$tmp_branch" FETCH_HEAD --quiet
    
    # Clean up the fake directory if we created it
    if [ "$created_fake_dir" = true ]; then
        rm -d "$src_dir" 2>/dev/null || rm -rf "$src_dir"
    fi
    
    # 4. Add or merge the subdirectory into our local path
    if [ ! -d "$dest_dir" ]; then
        # First time setup
        git subtree add --prefix="$dest_dir" "$tmp_branch" --squash -m "chore: add $dest_dir from external"
    else
        # Update existing (the '|| true' ignores errors if already up-to-date)
        git subtree merge --prefix="$dest_dir" "$tmp_branch" --squash -m "chore: update $dest_dir from external" || true
    fi
    
    # 5. Cleanup
    git branch -D "$tmp_branch" --quiet
}
