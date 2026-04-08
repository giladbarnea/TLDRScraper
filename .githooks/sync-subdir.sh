#!/usr/bin/env bash

# Fetches a subdirectory from a remote repo into a local path without committing —
# files materialize in the working tree only (untracked).
sync_untracked() {
    local repo_url="$1"
    local src_dir="$2"
    local dest_dir="$3"

    echo "==> Syncing $src_dir from $repo_url into $dest_dir"
    git fetch "$repo_url" main --quiet
    mkdir -p "$dest_dir"
    git archive FETCH_HEAD:"$src_dir" | tar -x -C "$dest_dir"
}
