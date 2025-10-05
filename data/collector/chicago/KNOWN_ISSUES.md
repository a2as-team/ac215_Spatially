# Known Issues - Chicago Municipal Code Collector

## Download Issue - RESOLVED ✓

**Status:** Resolved
**Date Resolved:** 2025-10-04

### Issue Description

The collector was not completing downloads because it was missing a critical step in the workflow.

### Root Cause

After clicking "Save PDF", the website:
1. Shows a bottom bar with "Preparing 1 item..." and a progress bar
2. The server prepares the file (takes 5-10 minutes for large files)
3. When ready, shows "1 item available" with an "OPEN" button
4. **The "OPEN" button must be clicked to actually trigger the download**

The initial implementation was waiting for a download that never started because it didn't click the "OPEN" button.

### Solution

Updated `collector/chicago/base.py` to:
1. After clicking "Save PDF", wait for the "OPEN" button to appear (class: `request__open`)
2. Click the "OPEN" button to trigger the actual download
3. Then wait for the download to complete

### Current Status

**Core functionality:** ✓ Complete
**Download automation:** ✓ Working in both headless and non-headless modes
**File validation:** ✓ Complete
**Error handling:** ✓ Complete

The collector successfully downloads the Chicago Municipal Code PDF (~30MB) in approximately 7-9 minutes.
