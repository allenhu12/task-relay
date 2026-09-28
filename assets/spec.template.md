---
Type: spec
Status: Active
Author: {AUTHOR}
Created: {YYYY-MM-DD}
---

# Source Code Reference on local workstation
<!-- All paths are on the local workstation's local storage -->

Set these values during task-relay initialization. Do not leave
`{PROJECT_ROOT}` unresolved in a live project spec, and never leave the
`Dashboard language` field as the template placeholder.

- PROJECT_ROOT: `{PROJECT_ROOT}`
- Example PROJECT_ROOT: `/path/to/workspace/example-project`
- Dashboard language: `none`
  <!-- REQUIRED. Ask the user during initialization which language the dashboard
       should show, then write the answer here as a code such as `zh-CN`, or
       `none` to show the stored text as written. A code turns on dashboard
       translation (D16); `none` turns it off. The agent may edit this one line
       later only after asking the user. -->
- Other sibling checkouts can use the same repo map, for example `/path/to/workspace/example-build-tools`.
- Controller: `{PROJECT_ROOT}/src/controller`
- example-service daemon: `{PROJECT_ROOT}/src/apps/example-service`
- Librsm: `{PROJECT_ROOT}/src/libs/example-lib`
- Kernel / network stack: `{PROJECT_ROOT}/opensource/linux/kernels/linux-5.4_12_5`
- Driver: `{PROJECT_ROOT}/src/platform_dp/linux/driver/vendor_example_11be_12_5`

## Multi-Repo Manifest Reference

Set `REPO_PROFILE_ROOT` to the profile folder that contains `manifest.xml`,
`metadata.json`, `repo_map.txt`, and `repo_map_upstream.txt`.

- REPO_PROFILE_ROOT: `{REPO_PROFILE_ROOT}`
- Example REPO_PROFILE_ROOT: `/path/to/profiles/example-release`
- Manifest source: `{REPO_PROFILE_ROOT}/manifest.xml`

Remote:
- Name: `{remote_name}`
- Fetch URL: `{remote_fetch_url}`
- Review URL: `{remote_review_url}`

Usage:
- Treat the manifest relative path as the repo checkout path under `{PROJECT_ROOT}`.
- If a manifest project has no explicit `path`, its checkout path is the same as its repo name.
- Repo local path format: `{PROJECT_ROOT}/<checkout_path>`.
- Before editing or running git commands, identify which repo owns the target file.
- During initialization, replace the placeholder table below with rows generated from `{REPO_PROFILE_ROOT}/manifest.xml`.

| Repo name | Checkout path | Local path | Upstream branch | Pinned revision |
|---|---|---|---|---|
| `{repo_name}` | `{checkout_path}` | `{PROJECT_ROOT}/{checkout_path}` | `{upstream_branch}` | `{pinned_revision}` |

# Compiling Server
Code is synced from local workstation to a remote Ubuntu 20.04 server and compiled inside a Docker container.

**Rule: whenever source files are modified, always provide a single `rsync` command that syncs exactly those files (file-level granularity, not directory-level).**

- Host: `user@build-host`
- TARGET_ROOT: `{TARGET_ROOT}`
- Example TARGET_ROOT: `/home/user/workspace/example-project`
- Compile root: `{TARGET_ROOT}/opensource/build-system-23-05`

rsync template:
```bash
PROJECT_ROOT="{PROJECT_ROOT}"
TARGET_ROOT="{TARGET_ROOT}"
CHANGED_FILE="relative/path/to/changed/file"

rsync -az --partial --info=progress2 \
    "$PROJECT_ROOT/$CHANGED_FILE" \
    "user@build-host:$TARGET_ROOT/$CHANGED_FILE"
```

# local document reference
## High Level Design
- `~/Document/HLD.md`
## Protocol Spec reference
- `~/Document/Protocol.pdf`

# web document reference
### Example Controller, Example Product, and Companion Product MR branches and release info
<INTERNAL_DOCUMENTATION_URL>

Summary: This Confluence page is the overall release matrix for Example Controller, Example Product, and Blue releases, mapping each version to its controller branch, AP branch, compatible release, supported AP models, and release notes. For LLM agents, use it to identify the correct branch and AP-family context before interpreting build, firmware, or test-environment details.

### Example Product and Example Controller MR branches and release info
<INTERNAL_DOCUMENTATION_URL>

Summary: This is the same Confluence page ID as the overall release-info page, with detailed Example Controller and Example Product release histories including GA, MR, refresh, patch, build number, and image/symbol references. For this project, the key current context is the Example Product 200.19 line, including 200.19.7.11 and 200.19.7.112 branch alignment.
