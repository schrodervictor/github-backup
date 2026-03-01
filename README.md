# GitHub Repository Data Backup

Backs up all non-git data from a GitHub repository into the `.github` directory
of the local clone. While `git clone --mirror` preserves commits, branches, and
tags, it does not capture issues, pull requests, reviews, discussions, and other
platform-specific data. This tool fills that gap.
