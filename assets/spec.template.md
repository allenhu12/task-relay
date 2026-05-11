---
Type: spec
Status: Active
Author: {AUTHOR}
Created: {YYYY-MM-DD}
---

# Source Code Reference on local workstation
<!-- All paths are on the local workstation's local storage -->

- Base: `/path/to/workspace/example-project`
- Librsm: `/path/to/workspace/example-project/src/example-lib`
- Kernel / network stack: `/path/to/workspace/example-project/opensource/linux/kernels/linux-5.4_12_5`
- Driver: `/path/to/workspace/example-project/src/platform_dp/linux/driver/vendor_example_11be_12_5`

# Compiling Server
Code is synced from local workstation to a remote Ubuntu 20.04 server and compiled inside a Docker container.

**Rule: whenever source files are modified, always provide a single `rsync` command that syncs exactly those files (file-level granularity, not directory-level).**

- Host: `user@build-host`
- Compile root: `/home/user/workspace/example-project/opensource/build-system-23-05`

rsync template:
```bash
rsync -az --partial --info=progress2 \
    "/path/to/workspace/example-project/src/example-lib/CHANGED_FILE" \
    user@build-host:/home/user/workspace/example-project/src/CHANGED_FILE
```

# local document reference
## High Level Design
- `~/Document/HLD.md`
## Protocol Spec reference
- `~/Document/Protocol.pdf`

# web document reference
- url
