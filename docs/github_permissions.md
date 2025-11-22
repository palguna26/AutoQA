# GitHub App Permissions

## Overview

This document outlines the required permissions for the AutoQA GitHub App.

## Recommended Permissions

### Minimum Required Permissions

| Permission | Access Level | Reason |
|------------|--------------|--------|
| Issues | Read & Write | Post checklist comments on issues |
| Pull Requests | Read & Write | Post review comments, read PR metadata |
| Checks | Write | Create check runs for validation status |
| Actions | Read | Read workflow runs and artifacts |
| Contents | Read | Read repository contents and PR diffs |

### Optional Permissions

| Permission | Access Level | Reason |
|------------|--------------|--------|
| Contents | Write | Push test files to test branches (not recommended) |
| Metadata | Read-only | Always required, automatically included |

## Permission Details

### Issues: Read & Write

**Required for:**
- Reading issue descriptions to extract acceptance criteria
- Posting checklist comments on issues
- Adding labels (optional)

**Why Read & Write:**
- Write access is needed to post comments

### Pull Requests: Read & Write

**Required for:**
- Reading PR diffs and metadata
- Posting review comments with compliance reports
- Reading PR body to find linked issues

**Why Read & Write:**
- Write access is needed to post comments

### Checks: Write

**Required for:**
- Creating check runs to show validation status
- Updating check run status based on CI results

**Why Write:**
- Create and update check runs programmatically

### Actions: Read

**Required for:**
- Reading workflow run status
- Downloading workflow artifacts (JUnit XML)
- Listing artifacts for a workflow run

**Why Read:**
- Need to fetch test results from CI workflows

### Contents: Read

**Required for:**
- Reading PR diffs (via API)
- Reading repository structure

**Why Read:**
- Need to analyze code changes for test generation

### Contents: Write (Optional, Not Recommended)

**Only if:**
- Pushing generated test files to test branches
- This is not the recommended approach

**Why Not Recommended:**
- Increases security surface area
- Better to use workflow dispatch to trigger CI

## Setup Instructions

### 1. Configure Permissions

1. Go to GitHub App settings
2. Navigate to "Permissions & events"
3. Set permissions as listed above

### 4. Subscribe to Events

Enable webhook events:
- ✅ `issues` - For issue opened events
- ✅ `pull_request` - For PR opened/synchronize events
- ✅ `workflow_run` - For CI completion events

### 3. Save Changes

1. Click "Save changes"
2. If app is already installed, reinstall to apply new permissions

## Security Considerations

### Least Privilege

- Start with minimum required permissions
- Only add additional permissions if needed
- Regularly review and audit permissions

### Webhook Secret

- Always use a strong webhook secret
- Store securely (environment variable, secret manager)
- Never commit to repository

### Private Key

- Private key should never be committed
- Store in secure environment variable
- Rotate periodically

## Troubleshooting

### Permission Errors

If you see errors like:
- `Resource not accessible by integration`
- `403 Forbidden`

**Solutions:**
1. Verify app has required permissions
2. Reinstall the app to refresh permissions
3. Check if repository/organization has restrictions
4. Verify installation has access to the repository

### Check Run Creation Fails

If check runs can't be created:
1. Verify "Checks: Write" permission is enabled
2. Check that app is installed on the repository
3. Verify installation has correct permissions

### Can't Read Workflow Artifacts

If artifacts can't be downloaded:
1. Verify "Actions: Read" permission is enabled
2. Check that workflow run is accessible to the app
3. Verify artifact exists and is not expired

## Permission Matrix

| Action | Required Permission |
|--------|-------------------|
| Post issue comment | Issues: Write |
| Read issue body | Issues: Read |
| Post PR comment | Pull Requests: Write |
| Read PR diff | Pull Requests: Read |
| Create check run | Checks: Write |
| Read workflow run | Actions: Read |
| Download artifact | Actions: Read |
| Read repository contents | Contents: Read |

