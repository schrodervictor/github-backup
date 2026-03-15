# GitHub Repository Data Backup

Backs up all non-git data from a GitHub repository into the `.github` directory
of the local clone. While `git clone --mirror` preserves commits, branches, and
tags, it does not capture issues, pull requests, reviews, discussions, and other
platform-specific data. This tool fills that gap.

The repository owner and name are detected automatically from the `origin`
remote.

## Requirements

- Python 3.10+
- `requests` library (`pip install requests`)
- A GitHub [personal access token](https://github.com/settings/tokens) with
  `repo` scope (and `read:project` for classic projects, `read:discussion` for
  discussions, `read:packages` for packages)
- Must be run from within a git repository with a GitHub `origin` remote

## Usage

```bash
# From within your repository
cd /path/to/your/repo

# Using an environment variable (recommended)
export GITHUB_TOKEN="ghp_..."
python -m github_backup

# Passing the token directly
python -m github_backup --token ghp_...

# Custom output directory (default: .github)
python -m github_backup --output-dir /path/to/output

# Incremental backup (only fetch data updated since last run)
python -m github_backup --incremental

# Incremental backup with an explicit cutoff timestamp
python -m github_backup --since 2024-06-01T00:00:00Z
```

## Project Structure

```
github_backup/
├── __main__.py          # CLI entry point and orchestrator
├── config.py            # Centralized configuration (base_dir, repo detection)
├── client.py            # GitHubClient — HTTP, pagination, rate limits, GraphQL
├── utils.py             # File save helpers (JSON, text, binary)
├── reactions.py         # Reaction fetching and saving helpers
├── simple.py            # Metadata, labels, milestones, projects, commit comments
├── issues.py            # Issues with comments, events, timeline, reactions
├── pulls.py             # PRs with diffs, comments, reviews, reactions
├── releases.py          # Releases with asset downloads
├── workflows.py         # Actions workflows and run history with logs
├── discussions.py       # Discussions via GraphQL with comments and replies
├── packages.py          # Packages backup orchestration (metadata and versions)
└── downloaders/         # Package file downloaders (one per registry type)
    ├── __init__.py      # Downloader registry and @downloader decorator
    ├── container.py     # Container/Docker images via GHCR OCI API
    ├── npm.py           # npm tarballs
    ├── maven.py         # Maven JARs
    ├── nuget.py         # NuGet .nupkg files
    └── rubygems.py      # RubyGems .gem files
```

Each module exports a single `backup(client)` function. To add a new resource
type, create a new module and add it to `STEP_REGISTRY` in `__main__.py`.

## What Gets Backed Up

| Data                | Source   | Details                                                                                                         |
| ------------------- | -------- | --------------------------------------------------------------------------------------------------------------- |
| Repository metadata | REST API | Description, topics, visibility, default branch, etc                                                            |
| Labels              | REST API | All labels with name, color, and description                                                                    |
| Milestones          | REST API | All milestones (open and closed)                                                                                |
| Issues              | REST API | All issues with comments, events, full timeline, and reactions                                                  |
| Pull requests       | REST API | All PRs with diff, comments, reviews, review comments, per-review comments, commits, and reactions on all items |
| Releases            | REST API | All releases with asset metadata and downloaded binary assets                                                   |
| Actions workflows   | REST API | Workflow definitions                                                                                            |
| Actions runs        | REST API | All workflow runs with jobs and log archives (zip)                                                              |
| Classic projects    | REST API | Project boards (v1)                                                                                             |
| Commit comments     | REST API | Comments made directly on commits                                                                               |
| Discussions         | GraphQL  | All discussions with fully paginated comments and nested replies                                                |
| Packages            | REST API | All packages (container, npm, maven, nuget, rubygems) with version metadata and downloaded package files        |

## Output Directory Structure

```
.github/
│
├── last_backup.json                     # Timestamp of last successful backup (for --incremental)
├── metadata.json                        # Repository metadata
├── labels.json                          # All labels
├── milestones.json                      # All milestones (open and closed)
├── projects.json                        # Classic project boards
├── commit_comments.json                 # Comments on commits
│
├── issues/
│   ├── index.json                       # All issues (summary list)
│   └── <number>/
│       ├── issue.json                   # Issue detail
│       ├── reactions.json               # Reactions on the issue itself
│       ├── comments.json                # Conversation comments
│       ├── comments/<comment_id>/
│       │   └── reactions.json           # Reactions on a specific comment
│       ├── events.json                  # Events (close, reopen, label, assign, etc.)
│       └── timeline.json               # Full timeline of all activity
│
├── pulls/
│   ├── index.json                       # All pull requests (summary list)
│   └── <number>/
│       ├── pull.json                    # PR detail
│       ├── diff.patch                   # Full diff in unified format
│       ├── reactions.json               # Reactions on the PR itself
│       ├── comments.json                # Conversation comments
│       ├── comments/<comment_id>/
│       │   └── reactions.json           # Reactions on a specific comment
│       ├── reviews.json                 # Review objects (approve, request changes, etc.)
│       ├── review_comments.json         # All inline diff comments on the PR
│       ├── review_comments/<comment_id>/
│       │   └── reactions.json           # Reactions on a specific inline comment
│       ├── commits.json                 # Commits included in the PR
│       └── reviews/<review_id>/
│           ├── comments.json            # Comments belonging to a specific review
│           └── reactions.json           # Reactions on the review itself
│
├── releases/
│   ├── index.json                       # All releases (summary list)
│   └── <tag>/
│       ├── release.json                 # Release detail with asset metadata
│       └── assets/
│           └── <filename>               # Downloaded binary assets
│
├── discussions/
│   ├── index.json                       # All discussions with inline comments
│   └── <number>/
│       └── discussion.json              # Discussion with comments and nested replies
│
├── actions/
│   ├── workflows.json                   # GitHub Actions workflow definitions
│   └── runs/
│       ├── index.json                   # All workflow runs (summary list)
│       └── <run_id>/
│           ├── run.json                 # Run detail (status, conclusion, timing, etc.)
│           ├── jobs.json                # Jobs within the run (steps, outcomes)
│           └── logs.zip                 # Full run logs (if not expired)
│
└── packages/
    ├── index.json                       # All packages linked to this repo
    └── <package_type>/<package_name>/
        ├── package.json                 # Package metadata
        ├── versions.json                # All versions (summary list)
        └── <version>/
            ├── version.json             # Version metadata
            ├── manifest.json            # (container) OCI image manifest
            ├── blobs/                   # (container) Config and layer blobs
            │   └── sha256_<digest>
            ├── platforms/               # (container) Per-platform manifests and blobs
            │   └── <os>_<arch>/
            ├── <name>-<version>.tgz     # (npm) Package tarball
            ├── <artifact>-<version>.jar # (maven) JAR file
            ├── <name>.<version>.nupkg   # (nuget) NuGet package
            └── <name>-<version>.gem     # (rubygems) Gem file
```

## Incremental Backups

By default the tool performs a full backup. Use `--incremental` to only fetch
data that changed since the last successful run. The cutoff timestamp is stored
in `last_backup.json` inside the output directory.

- **Issues & Pull requests**: The GitHub `/issues?since=` parameter returns
  items whose `updated_at` is newer than the cutoff. Each matched item is then
  fully re-backed-up (all comments, reviews, events, etc.).
- **Workflow runs**: Filtered server-side via `created>=TIMESTAMP`.
- **Discussions**: Ordered by `UPDATED_AT DESC` in GraphQL; pagination stops
  once all recent discussions have been collected.
- **Releases**: Filtered client-side by `published_at` / `created_at`.
- **Packages**: All versions are fetched and filtered client-side by
  `updated_at` / `created_at`. Only new or updated versions are downloaded.
- **Simple resources** (labels, milestones, projects, etc.): Always fetched in
  full — they are cheap and don't support incremental queries.

Index files (e.g. `issues/index.json`) are **merged** during incremental runs:
updated entries replace their older versions while previously backed-up entries
are preserved.

## Resilience

- **Rate limiting**: The script monitors `X-RateLimit-Remaining` headers and
  automatically sleeps until the rate limit resets.
- **Retries**: Server errors (5xx) are retried up to 3 times with exponential
  backoff.
- **Graceful skipping**: Endpoints that return 404 (not found), 410 (gone), or
  422 (unprocessable) are skipped without aborting the entire backup. This
  handles cases like repositories with discussions disabled.
- **Layered GraphQL pagination**: Discussions, comments, and replies are each
  paginated in separate queries to avoid GitHub's node limit (which caps the
  product of nested `first` values at 500,000 nodes).
