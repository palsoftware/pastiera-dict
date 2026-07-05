# pastiera-dict

Asset repository for Pastiera dictionaries (`.dict`) and downloadable keyboard layouts (`.json`).

This repo is the companion to the main app repo (`palsoftware/pastiera`) and is used to keep APK size under control by distributing large assets separately through GitHub Releases + GitHub Pages manifests.

## Repository Roles

- `palsoftware/pastiera`
  - App source code
  - Bundled/default assets used directly in the APK
  - Locale integration (`method.xml`, `strings.xml`, `locale_layout_mapping.json`)
- `palsoftware/pastiera-dict` (this repo)
  - Release-distributed dictionaries (`dicts/*.dict`)
  - Release-distributed layouts (`layouts/*.json`)
  - Manifests served via GitHub Pages (`docs/*.json`)

## Folder Layout

- `dicts/`: dictionary binaries to upload as release assets (`*_base.dict`)
- `layouts/`: downloadable keyboard layouts (`*.json`)
- `docs/dicts-manifest.json`: generated dictionary manifest (GitHub Pages)
- `docs/layouts-manifest.json`: generated layout manifest (GitHub Pages)
- `docs/dicts-metadata.json`: manually maintained dictionary display metadata
- `docs/APP_INTEGRATION.md`: app-side retrieval/integration notes
- `docs/RELEASE_PROCESS.md`: release + manifest automation details

## Corpus Sources and Credits

Some dictionary assets are built from public monolingual corpora.
For this project we use data from the Leipzig Corpora Collection where applicable.

Reference:

- D. Goldhahn, T. Eckart, U. Quasthoff: *Building Large Monolingual Dictionaries at the Leipzig Corpora Collection: From 100 to 200 Languages*. Proceedings of LREC 2012, 2012.

Source:

- https://wortschatz-leipzig.de/de/download/

The Czech, Hungarian, Swedish and Turkish dictionary assets are built from the top 50,000
frequency-ranked, letter-only entries in these Leipzig Corpora Collection
frequency lists:

- `cs_base.dict`: `ces_news_2023_1M/ces_news_2023_1M-words.txt`
  from `ces_news_2023_1M.tar.gz`
  (`0625e5f1e76a5e574268912e99af686ae9a15e980bbd9c8d177f880e78af2f84`)
- `hu_base.dict`: `hun_news_2023_1M/hun_news_2023_1M-words.txt`
  from `hun_news_2023_1M.tar.gz`
  (`cc9a1d3e38b3e1ae704bf6c7de03ec70a498f05a2f699dea0ccb6666b304b8a8`)
- `sv_base.dict`: `swe_news_2023_1M/swe_news_2023_1M-words.txt`
  from `swe_news_2023_1M.tar.gz`
  (`899447b8d42d2acca48d0c193a571678cac814e761329895d0e55ac37ad075c9`)
- `tr_base.dict`: `tur_news_2023_1M/tur_news_2023_1M-words.txt`
  from `tur_news_2023_1M.tar.gz`
  (`abfae1f81bb7222c984afb40a06cc8d0e54376d43ea3f9b35e88412863f0b68e`)

The Greek dictionary asset (`el_base.dict`) is built from the top 50,000
frequency-ranked, letter-only entries in the eellak GSOC 2019 Greek spelling
dictionary with frequencies (`data/spell_dict_with_freq.dic`).

Reference:

- Konstantinos Agiannis et al.: *Development of a Greek open source Morphological dictionary and application of it to Greek spelling tools*, GSOC 2019.

Source:

- https://github.com/eellak/gsoc2019-greek-morpho

License:

- Source code: GPLv3
- Produced morphological database: CC BY-SA 3.0

## Cross-Repo Workflow (Practical)

### 1. Add language support in `pastiera`

In the app repo:

- add layout JSON under `app/src/main/assets/common/layouts/`
- add locale mapping in `app/src/main/assets/common/locale_layout_mapping.json`
- add IME subtype label in `app/src/main/res/values/strings.xml`
- add subtype in `app/src/main/res/xml/method.xml`
- add translations (`values-xx/strings.xml`) as needed
- optionally add dictionary assets to the app PR if immediate bundled support is required

Notes:

- Be careful with `app/src/main/assets/common/variations/variations.json`:
  - it is global, not locale-scoped
  - locale-specific characters can unintentionally affect other languages
- Prefer putting language-specific reachability into the layout (multi-tap) where possible.

### 2. Move downloadable assets into `pastiera-dict`

In this repo:

- add `dicts/<lang>_base.dict`
- add `layouts/<layout>.json` (must include `name` + `description`)
- add dictionary metadata in `docs/dicts-metadata.json`:
  - `name`
  - `shortDescription`
  - `languageTag`

Notes:

- `docs/dicts-manifest.json` and `docs/layouts-manifest.json` are generated from releases.
- Manual edits to manifests should be rare (e.g. typo correction) and ideally followed by the next automated release update.

### 3. Publish release in `pastiera-dict`

- create a GitHub Release
- upload the new `.dict` / `.json` assets
- publish release

The GitHub Actions workflow runs `update_manifests.py` and updates:

- `docs/dicts-manifest.json`
- `docs/layouts-manifest.json`

These manifests are consumed by the app via GitHub Pages.

## Maintainer Checklist (Before Merge / Release)

- layout JSON parses and contains `name` / `description`
- no empty or invalid multi-tap entries
- locale integrations in `pastiera` keep existing locales intact (merge conflicts often happen here)
- translation files have valid format placeholders (`%1$s`, `%1$d`, etc.)
- `dicts-metadata.json` contains metadata for any new dictionary IDs
