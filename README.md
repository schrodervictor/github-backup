# GitHub Repository Data Backup

Backs up all non-git data from a GitHub repository into the `.github` directory
of the local clone. While `git clone --mirror` preserves commits, branches, and
tags, it does not capture issues, pull requests, reviews, discussions, and other
platform-specific data. This tool fills that gap.

The repository owner and name are detected automatically from the `origin`
remote.

## Requirements

- Python 3.7+
- `requests` library (`pip install requests`)
- A GitHub [personal access token](https://github.com/settings/tokens) with
  `repo` scope (and `read:project` for classic projects, `read:discussion` for
  discussions)
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
└── discussions.py       # Discussions via GraphQL with comments and replies
```

Each module exports a single `backup(client)` function. To add a new resource
type, create a new module and add it to `BACKUP_STEPS` in `__main__.py`.

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

## Output Directory Structure

```
.github/
│
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
└── actions/
    ├── workflows.json                   # GitHub Actions workflow definitions
    └── runs/
        ├── index.json                   # All workflow runs (summary list)
        └── <run_id>/
            ├── run.json                 # Run detail (status, conclusion, timing, etc.)
            ├── jobs.json                # Jobs within the run (steps, outcomes)
            └── logs.zip                 # Full run logs (if not expired)
```

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
