# Release Process and Automation Documentation

This document describes the automated release process for dictionary and keyboard layout assets, including how manifests are generated and updated.

## Overview

This repository distributes:
- **Dictionary files** (`.dict`, ~15–25 MB) as GitHub Release assets
- **Keyboard layout files** (`.json`, small) as GitHub Release assets
- **Manifest files** served via GitHub Pages:
  - `docs/dicts-manifest.json` - Dictionary manifest
  - `docs/layouts-manifest.json` - Layout manifest

All asset management is fully automated through GitHub Actions workflows and Python scripts.

## Manifest Structure

### Dictionary Manifest (`docs/dicts-manifest.json`)

Each dictionary entry contains:

**Technical fields:**
- `id` - Stable identifier (e.g., `"de_base"`)
- `filename` - Asset filename (e.g., `"de_base.dict"`)
- `url` - Public download URL from GitHub Release
- `bytes` - File size in bytes
- `sha256` - SHA-256 hash of the file
- `updatedAt` - ISO 8601 timestamp of last update

**UI-friendly fields:**
- `name` - Display name (e.g., `"German (Basic)"`)
- `shortDescription` - Single-line description (e.g., `"Common words • lightweight"`)
- `languageTag` - BCP 47 language tag (e.g., `"de-DE"`)

**Top-level fields:**
- `schemaVersion` - Manifest schema version (integer, currently `1`)
- `generatedAt` - ISO 8601 timestamp of manifest generation
- `releaseTag` - GitHub Release tag that triggered this update

### Layout Manifest (`docs/layouts-manifest.json`)

Layout entries have the same structure as dictionaries, but:
- `name` and `shortDescription` are automatically extracted from the layout JSON file
- `languageTag` is typically empty (layouts are keyboard mappings, not language-specific)

## Release Process

### Step 1: Prepare Assets

1. **Dictionary files** (`.dict`):
   - Binary files (~15–25 MB)
   - No embedded metadata
   - Must be added to `docs/dicts-metadata.json` for UI fields

2. **Layout files** (`.json`):
   - JSON files containing keyboard mappings
   - Must include `name` and `description` fields in the JSON
   - Automatically parsed for manifest metadata

### Step 2: Create GitHub Release

1. Go to GitHub Releases page
2. Click "Draft a new release"
3. Create a new tag (e.g., `v1.0.0`, `2`, etc.)
4. Upload all `.dict` and `.json` files as release assets
5. Publish the release

### Step 3: Automatic Manifest Update

When a release is published, the GitHub Actions workflow automatically:

1. **Triggers** on `release: types: [published]`
2. **Checks out** the repository (default branch)
3. **Fetches latest** version to ensure up-to-date manifests
4. **Runs** `update_manifests.py` script
5. **Commits and pushes** updated manifests

The workflow can also be triggered manually via "Run workflow" with optional parameters:
- `release_tag` - Process a specific release tag
- `tag_pattern` - Process latest release matching a pattern (e.g., `v*`)

## Automation Components

### Python Script: `update_manifests.py`

The core automation script that generates and updates manifest files.

#### Features

1. **Fetches release assets** from GitHub API
   - Supports specific release tag, tag pattern, or latest release
   - Uses GitHub token for authentication (if provided)

2. **Preserves existing items**
   - Loads existing manifest files
   - Maintains all items not present in the new release
   - Only updates items that appear in the new release

3. **Updates existing items**
   - When the same asset (same ID) appears in a new release:
     - Updates `url` to point to new release
     - Updates `bytes` with new file size
     - Updates `sha256` with new hash
     - Updates `updatedAt` timestamp
   - Preserves UI fields (`name`, `shortDescription`, `languageTag`)

4. **Adds new items**
   - Derives stable ID from filename (removes extension, normalizes)
   - Computes SHA-256 hash by downloading the asset
   - For dictionaries: loads metadata from `docs/dicts-metadata.json`
   - For layouts: extracts `name` and `description` from JSON file

5. **ID stability**
   - Once an ID exists in the manifest, it is preserved
   - IDs are derived deterministically from filenames
   - Prevents automatic renaming of established IDs

#### Usage

```bash
python3 update_manifests.py \
  --owner OWNER \
  --repo REPO \
  [--release-tag TAG] \
  [--tag-pattern PATTERN] \
  [--dicts-manifest PATH] \
  [--layouts-manifest PATH] \
  [--dicts-metadata PATH]
```

**Parameters:**
- `--owner` (required) - GitHub repository owner
- `--repo` (required) - GitHub repository name
- `--release-tag` (optional) - Specific release tag to process
- `--tag-pattern` (optional) - Pattern to match releases (e.g., `v*`)
- `--dicts-manifest` (optional) - Path to dicts manifest (default: `docs/dicts-manifest.json`)
- `--layouts-manifest` (optional) - Path to layouts manifest (default: `docs/layouts-manifest.json`)
- `--dicts-metadata` (optional) - Path to dicts metadata (default: `docs/dicts-metadata.json`)

**Environment variables:**
- `GITHUB_TOKEN` - GitHub personal access token (optional, for private repos or rate limits)

### GitHub Actions Workflow: `.github/workflows/update-manifests.yml`

Automated workflow that runs on release publication.

#### Triggers

1. **Automatic**: `release: types: [published]`
   - Triggers when a release is published
   - Uses the published release tag automatically

2. **Manual**: `workflow_dispatch`
   - Can be triggered manually from GitHub Actions UI
   - Optional inputs:
     - `release_tag` - Process specific release
     - `tag_pattern` - Process latest matching release

#### Workflow Steps

1. **Checkout repository**
   - Checks out default branch
   - Full history (`fetch-depth: 0`)

2. **Ensure latest version**
   - Fetches and resets to latest remote state
   - Ensures manifest files are up-to-date before processing

3. **Set up Python**
   - Installs Python 3.11

4. **Run manifest updater**
   - Executes `update_manifests.py` with appropriate parameters
   - Uses `GITHUB_TOKEN` for API authentication

5. **Commit and push changes**
   - Stages updated manifest files
   - Commits with message: `"chore: update manifests from release {TAG}"`
   - Pushes to default branch
   - Skips commit if no changes detected

#### Permissions

- `contents: write` - Required to commit and push manifest updates
- `pull-requests: write` - Available for future PR-based workflows

## Dictionary Metadata Management

### File: `docs/dicts-metadata.json`

This file maps dictionary IDs to UI-friendly metadata.

#### Structure

```json
{
  "dictionary_id": {
    "name": "Display Name",
    "shortDescription": "Single-line description",
    "languageTag": "lang-REGION"
  }
}
```

#### Example

```json
{
  "de_base": {
    "name": "German (Basic)",
    "shortDescription": "Common words • lightweight",
    "languageTag": "de-DE"
  }
}
```

#### Adding New Dictionary Metadata

1. Add entry to `docs/dicts-metadata.json`:
   ```json
   {
     "new_dict_id": {
       "name": "New Dictionary",
       "shortDescription": "Description here",
       "languageTag": "en-US"
     }
   }
   ```

2. Commit the metadata file
3. When the dictionary asset is released, the manifest will automatically use this metadata

#### Fallback Behavior

If a dictionary ID is missing from `dicts-metadata.json`:
- `name` is derived from ID (e.g., `"de_base"` → `"De Base"`)
- `shortDescription` is empty
- `languageTag` is empty
- A warning is logged: `"Warning: Missing metadata for dictionary 'ID'. Please add it to dicts-metadata.json"`

## Layout Metadata Extraction

Layout metadata is automatically extracted from the layout JSON files.

### Required JSON Structure

Layout files must include:
```json
{
  "name": "Layout Name",
  "description": "Layout description (can be multi-line)",
  "mappings": { ... }
}
```

### Extraction Process

1. Script downloads the layout JSON from release asset URL
2. Parses JSON to extract `name` and `description` fields
3. Trims `description` to first line (single-line requirement)
4. Uses extracted values in manifest

If parsing fails, empty strings are used and a warning is logged.

## ID Stability and Derivation

### ID Derivation Rules

1. **Remove file extension** (`.dict` or `.json`)
2. **Remove version suffixes** (e.g., `_v1`, `-v2`, `.1.0`)
3. **Normalize**:
   - Convert to lowercase
   - Replace spaces and hyphens with underscores

**Examples:**
- `de_base.dict` → `de_base`
- `en_base_v2.dict` → `en_base`
- `Cyrillic_Translite.json` → `cyrillic_translite`

### ID Preservation

- Once an ID exists in a manifest, it is **never automatically changed**
- If a filename changes but the derived ID matches an existing ID, the existing ID is used
- This ensures stable references for consuming applications

### Handling Duplicates

If a derived ID conflicts with an existing ID:
- Append numeric suffix: `original_id_1`, `original_id_2`, etc.
- Only applies within the same processing batch

## Manifest Update Behavior

### Scenario 1: New Release with New Assets

**Release 1**: Contains `it_base.dict`, `fr_base.dict`
- Manifest contains: `it_base`, `fr_base`

**Release 2**: Contains `en_base.dict`
- Manifest contains: `it_base`, `fr_base` (preserved), `en_base` (new)

### Scenario 2: New Release with Updated Asset

**Release 1**: Contains `it_base.dict` (SHA-256: `abc123...`)
- Manifest: `it_base` with URL pointing to release 1

**Release 3**: Contains `it_base.dict` (SHA-256: `def456...`)
- Manifest: `it_base` updated with:
  - New URL pointing to release 3
  - New SHA-256: `def456...`
  - New `updatedAt` timestamp
  - Preserved UI fields (`name`, `shortDescription`, `languageTag`)

### Scenario 3: Mixed Update

**Release 1**: Contains `it_base.dict`, `fr_base.dict`
- Manifest: `it_base`, `fr_base`

**Release 2**: Contains `it_base.dict` (updated), `en_base.dict` (new)
- Manifest: 
  - `it_base` (updated with new release 2 URL/SHA-256)
  - `fr_base` (preserved from release 1)
  - `en_base` (new from release 2)

## Local Testing

You can test the script locally before creating a release:

```bash
# Test with latest release
python3 update_manifests.py --owner palsoftware --repo pastiera-dict

# Test with specific release
python3 update_manifests.py \
  --owner palsoftware \
  --repo pastiera-dict \
  --release-tag 2

# Test with tag pattern
python3 update_manifests.py \
  --owner palsoftware \
  --repo pastiera-dict \
  --tag-pattern "v*"
```

**Note**: Local testing requires:
- Python 3.11+
- Internet connection (to fetch release assets and compute SHA-256)
- Optional: `GITHUB_TOKEN` environment variable for private repos or rate limits

## Troubleshooting

### Manifest Missing Items from Previous Releases

**Symptom**: After a new release, manifest only contains items from the new release.

**Cause**: The workflow didn't fetch the latest manifest before processing.

**Solution**: The workflow now includes an "Ensure latest version" step that fetches and resets before processing. If this still occurs, check:
1. Workflow has `contents: write` permission
2. Default branch is correctly specified
3. Manifest files exist in the repository

### Missing Dictionary Metadata Warnings

**Symptom**: Script logs warnings about missing dictionary metadata.

**Solution**: Add the dictionary ID to `docs/dicts-metadata.json` with appropriate `name`, `shortDescription`, and `languageTag`.

### Layout Metadata Not Extracted

**Symptom**: Layout manifest has empty `name` or `shortDescription`.

**Cause**: Layout JSON file doesn't contain `name` or `description` fields.

**Solution**: Ensure layout JSON files include:
```json
{
  "name": "...",
  "description": "...",
  "mappings": { ... }
}
```

### SHA-256 Computation Fails

**Symptom**: Script fails when computing SHA-256.

**Cause**: Cannot download asset from GitHub Release URL.

**Solution**: 
- Check asset URL is accessible
- Verify `GITHUB_TOKEN` is set (for private repos)
- Check network connectivity

### Workflow Fails to Commit

**Symptom**: Workflow runs but doesn't commit changes.

**Cause**: No changes detected or permission issues.

**Solution**:
- Check workflow logs for "No changes to commit" message
- Verify `contents: write` permission is set
- Ensure default branch name is correct

## Best Practices

1. **Always add dictionary metadata** before releasing new dictionaries
2. **Test locally** before publishing releases
3. **Use consistent naming** for assets to ensure stable IDs
4. **Don't manually edit manifests** - they are auto-generated
5. **Commit metadata changes** separately from releases
6. **Verify manifest updates** after each release

## File Locations

- **Script**: `update_manifests.py` (repository root)
- **Workflow**: `.github/workflows/update-manifests.yml`
- **Dictionary manifest**: `docs/dicts-manifest.json`
- **Layout manifest**: `docs/layouts-manifest.json`
- **Dictionary metadata**: `docs/dicts-metadata.json`

## Schema Version

Current schema version: `1`

When making breaking changes to manifest structure, increment `SCHEMA_VERSION` in `update_manifests.py` and update this documentation.
