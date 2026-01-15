#!/usr/bin/env python3
"""
Automated manifest generator for dictionary and layout assets.

This script fetches assets from a GitHub Release and updates manifest files
while preserving stable IDs and existing metadata.
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse
from urllib.request import urlopen

SCHEMA_VERSION = 1


def compute_sha256(url: str) -> str:
    """Download file and compute SHA-256 hash."""
    with urlopen(url) as response:
        data = response.read()
        return hashlib.sha256(data).hexdigest()


def get_file_size(url: str) -> int:
    """Get file size from URL without downloading the full file."""
    with urlopen(url) as response:
        return int(response.headers.get('Content-Length', 0))


def derive_id_from_filename(filename: str, extension: str) -> str:
    """Derive stable ID from filename by removing extension and version suffix."""
    base = filename.replace(extension, '')
    # Remove common version patterns (e.g., _v1, -v2, .1.0)
    import re
    base = re.sub(r'[-_]v?\d+(\.\d+)*$', '', base)
    base = re.sub(r'\.\d+$', '', base)
    return base.lower().replace(' ', '_').replace('-', '_')


def load_existing_manifest(manifest_path: str) -> Dict:
    """Load existing manifest or return empty structure."""
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content and content != "hello world":
                    return json.loads(content)
        except (json.JSONDecodeError, IOError):
            pass
    
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": "",
        "releaseTag": "",
        "items": []
    }


def load_dicts_metadata(metadata_path: str) -> Dict[str, Dict[str, str]]:
    """Load dictionary metadata mapping file."""
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.loads(f.read())
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load dicts metadata: {e}", file=sys.stderr)
    return {}


def extract_layout_metadata(url: str) -> tuple[str, str]:
    """Download and parse layout JSON to extract name and description."""
    try:
        with urlopen(url) as response:
            layout_data = json.loads(response.read().decode('utf-8'))
            name = layout_data.get("name", "")
            description = layout_data.get("description", "")
            # Trim description to single line
            if description:
                description = description.split('\n')[0].strip()
            return name, description
    except Exception as e:
        print(f"Warning: Could not parse layout metadata from {url}: {e}", file=sys.stderr)
        return "", ""


def derive_readable_name_from_id(item_id: str) -> str:
    """Derive a readable name from ID as fallback."""
    # Convert "de_base" -> "de base" -> "De Base"
    parts = item_id.split('_')
    return ' '.join(word.capitalize() for word in parts)


def find_existing_item_by_id(items: List[Dict], item_id: str) -> Optional[Dict]:
    """Find existing item by ID."""
    for item in items:
        if item.get("id") == item_id:
            return item
    return None


def find_existing_item_by_filename(items: List[Dict], filename: str) -> Optional[Dict]:
    """Find existing item by filename (for ID preservation)."""
    for item in items:
        if item.get("filename") == filename:
            return item
    return None


def update_manifest(
    manifest_path: str,
    asset_type: str,
    release_tag: str,
    assets: List[Dict],
    extension: str,
    dicts_metadata: Optional[Dict[str, Dict[str, str]]] = None
) -> None:
    """Update manifest file with new asset information."""
    existing_manifest = load_existing_manifest(manifest_path)
    existing_items = existing_manifest.get("items", [])
    
    # Create mapping of existing IDs by filename for preservation
    id_by_filename = {}
    for item in existing_items:
        if "filename" in item and "id" in item:
            id_by_filename[item["filename"]] = item["id"]
    
    # Start with all existing items as base (preserve items not in this release)
    # Use dict keyed by ID for efficient lookup and updates
    updated_items_dict = {item.get("id"): item.copy() for item in existing_items}
    processed_ids = set()
    
    # Process each asset from the current release
    for asset in assets:
        filename = asset["name"]
        if not filename.endswith(extension):
            continue
        
        # Derive ID from filename first
        derived_id = derive_id_from_filename(filename, extension)
        
        # Try to find existing item by derived ID (preferred - stable even if filename changes)
        existing_item = find_existing_item_by_id(existing_items, derived_id)
        
        if existing_item:
            # Use existing ID (stable)
            item_id = existing_item.get("id")
        else:
            # Check if filename exists in manifest (backwards compatibility)
            item_id = id_by_filename.get(filename)
            if item_id:
                existing_item = find_existing_item_by_id(existing_items, item_id)
            else:
                # New item - use derived ID
                item_id = derived_id
        
        # Ensure ID uniqueness within this batch
        original_id = item_id
        counter = 1
        while item_id in processed_ids or (item_id in updated_items_dict and item_id != original_id):
            item_id = f"{original_id}_{counter}"
            counter += 1
        
        processed_ids.add(item_id)
        
        # Get asset metadata
        download_url = asset["browser_download_url"]
        file_size = asset["size"]
        
        # Compute SHA-256 (GitHub API doesn't provide it)
        print(f"Computing SHA-256 for {filename}...", file=sys.stderr)
        sha256 = compute_sha256(download_url)
        
        # Check if this is an update to an existing item or a new item
        is_update = item_id in updated_items_dict
        
        if is_update:
            # Update existing item with new release data
            item = updated_items_dict[item_id]
            print(f"Updating existing {asset_type} '{item_id}' from release {release_tag}", file=sys.stderr)
            # Update technical fields with new release data
            item["url"] = download_url
            item["bytes"] = file_size
            item["sha256"] = sha256
            item["updatedAt"] = datetime.utcnow().isoformat() + "Z"
            # Update filename if changed
            if "filename" not in item or item["filename"] != filename:
                item["filename"] = filename
        else:
            # New item - create from scratch
            print(f"Adding new {asset_type} '{item_id}' from release {release_tag}", file=sys.stderr)
            item = {
                "id": item_id,
                "filename": filename,
                "url": download_url,
                "bytes": file_size,
                "sha256": sha256,
                "updatedAt": datetime.utcnow().isoformat() + "Z"
            }
            updated_items_dict[item_id] = item
        
        # Add/update UI-friendly fields based on asset type
        if asset_type == "layout":
            # Parse layout JSON to extract name and description
            layout_name, layout_description = extract_layout_metadata(download_url)
            item["name"] = layout_name
            item["shortDescription"] = layout_description
            if "languageTag" not in item:
                item["languageTag"] = ""
        elif asset_type == "dictionary":
            # Use metadata mapping for dictionaries
            if dicts_metadata and item_id in dicts_metadata:
                metadata = dicts_metadata[item_id]
                item["name"] = metadata.get("name", "")
                item["shortDescription"] = metadata.get("shortDescription", "")
                item["languageTag"] = metadata.get("languageTag", "")
            else:
                # Fallback: derive readable name from ID (only if not already set)
                if "name" not in item or not item.get("name"):
                    item["name"] = derive_readable_name_from_id(item_id)
                if "shortDescription" not in item or not item.get("shortDescription"):
                    item["shortDescription"] = ""
                if "languageTag" not in item or not item.get("languageTag"):
                    item["languageTag"] = ""
                if not is_update:  # Only warn for new items, not updates
                    print(f"Warning: Missing metadata for dictionary '{item_id}'. Please add it to dicts-metadata.json", file=sys.stderr)
    
    # Convert dict to list and sort by ID for stable ordering
    updated_items_list = list(updated_items_dict.values())
    updated_items_list.sort(key=lambda x: x.get("id", ""))
    
    # Build final manifest
    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.utcnow().isoformat() + "Z",
        "releaseTag": release_tag,
        "items": updated_items_list
    }
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    
    # Write manifest
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"Updated {manifest_path} with {len(updated_items_list)} {asset_type} items", file=sys.stderr)


def fetch_release_assets(owner: str, repo: str, release_tag: Optional[str] = None, tag_pattern: Optional[str] = None) -> tuple[str, List[Dict]]:
    """Fetch release assets from GitHub API."""
    import urllib.request
    import base64
    import re
    
    # Build API URL
    if release_tag:
        url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{release_tag}"
    elif tag_pattern:
        # Fetch all releases and find the latest matching the pattern
        url = f"https://api.github.com/repos/{owner}/{repo}/releases"
        request = urllib.request.Request(url)
        request.add_header("Accept", "application/vnd.github.v3+json")
        
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            auth = base64.b64encode(f":{token}".encode()).decode()
            request.add_header("Authorization", f"Basic {auth}")
        
        try:
            with urlopen(request) as response:
                releases = json.loads(response.read().decode('utf-8'))
                pattern = re.compile(tag_pattern.replace('*', '.*'))
                for release in releases:
                    if pattern.match(release["tag_name"]):
                        release_tag = release["tag_name"]
                        assets = release.get("assets", [])
                        return release_tag, assets
                print(f"No release found matching pattern: {tag_pattern}", file=sys.stderr)
                sys.exit(1)
        except Exception as e:
            print(f"Error fetching releases: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    
    # Make request
    request = urllib.request.Request(url)
    request.add_header("Accept", "application/vnd.github.v3+json")
    
    # Add authentication if token is provided
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        auth = base64.b64encode(f":{token}".encode()).decode()
        request.add_header("Authorization", f"Basic {auth}")
    
    try:
        with urlopen(request) as response:
            release_data = json.loads(response.read().decode('utf-8'))
            release_tag = release_data["tag_name"]
            assets = release_data.get("assets", [])
            return release_tag, assets
    except Exception as e:
        print(f"Error fetching release: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Update manifest files from GitHub Release assets"
    )
    parser.add_argument(
        "--owner",
        required=True,
        help="GitHub repository owner"
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="GitHub repository name"
    )
    parser.add_argument(
        "--release-tag",
        help="Release tag (default: latest release)"
    )
    parser.add_argument(
        "--tag-pattern",
        help="Tag pattern to match (e.g., 'v*' for v1.0.0, v2.0.0, etc.)"
    )
    parser.add_argument(
        "--dicts-manifest",
        default="docs/dicts-manifest.json",
        help="Path to dictionaries manifest file"
    )
    parser.add_argument(
        "--layouts-manifest",
        default="docs/layouts-manifest.json",
        help="Path to layouts manifest file"
    )
    
    parser.add_argument(
        "--dicts-metadata",
        default="docs/dicts-metadata.json",
        help="Path to dictionaries metadata mapping file"
    )
    
    args = parser.parse_args()
    
    # Load dictionary metadata if it exists
    dicts_metadata = None
    if os.path.exists(args.dicts_metadata):
        dicts_metadata = load_dicts_metadata(args.dicts_metadata)
    
    # Fetch release assets
    release_tag, assets = fetch_release_assets(args.owner, args.repo, args.release_tag, args.tag_pattern)
    print(f"Processing release: {release_tag}", file=sys.stderr)
    print(f"Found {len(assets)} assets", file=sys.stderr)
    
    # Separate dictionaries and layouts
    dict_assets = [a for a in assets if a["name"].endswith(".dict")]
    layout_assets = [a for a in assets if a["name"].endswith(".json")]
    
    # Update manifests
    if dict_assets:
        update_manifest(
            args.dicts_manifest,
            "dictionary",
            release_tag,
            dict_assets,
            ".dict",
            dicts_metadata
        )
    else:
        print("No dictionary assets found", file=sys.stderr)
    
    if layout_assets:
        update_manifest(
            args.layouts_manifest,
            "layout",
            release_tag,
            layout_assets,
            ".json",
            None
        )
    else:
        print("No layout assets found", file=sys.stderr)


if __name__ == "__main__":
    main()
