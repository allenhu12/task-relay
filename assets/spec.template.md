---
Type: spec
Status: Active
Author: {AUTHOR}
Created: {YYYY-MM-DD}
---

# Source Code Reference
<!-- Replace every example with values for the current project. -->

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
- Main service: `{PROJECT_ROOT}/src/service`
- Command-line application: `{PROJECT_ROOT}/src/cli`
- Shared library: `{PROJECT_ROOT}/src/lib`
- Integration tests: `{PROJECT_ROOT}/tests/integration`
- Build configuration: `{PROJECT_ROOT}/build`

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

# Build Server
Code is synced from the local workstation to a remote Linux server and built inside a container.

**Rule: whenever source files are modified, always provide a single `rsync` command that syncs exactly those files (file-level granularity, not directory-level).**

- Host: `user@build-host`
- TARGET_ROOT: `{TARGET_ROOT}`
- Example TARGET_ROOT: `/home/user/workspace/example-project`
- Build root: `{TARGET_ROOT}/build`

rsync template:
```bash
PROJECT_ROOT="{PROJECT_ROOT}"
TARGET_ROOT="{TARGET_ROOT}"
CHANGED_FILE="relative/path/to/changed/file"

rsync -az --partial --info=progress2 \
    "$PROJECT_ROOT/$CHANGED_FILE" \
    "user@build-host:$TARGET_ROOT/$CHANGED_FILE"
```

# Local document reference
## High Level Design
- `~/Documents/architecture.md`
## Protocol specification
- `~/Documents/protocol.pdf`

# Web document reference
### Product release matrix
`<INTERNAL_RELEASE_MATRIX_URL>`

Summary: This internal page maps product versions to source branches, compatible components,
build identifiers, and release notes. Use it to select the correct branch and component context
before interpreting build or test-environment details.
