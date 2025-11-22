# CI Contract

## Overview

This document defines the contract between AutoQA and GitHub Actions workflows that run generated tests.

## Artifact Requirements

GitHub Actions workflows that run AutoQA-generated tests must produce a JUnit XML artifact with the following specifications:

### Artifact Name

- Name: `autoqa-test-report` (or any name containing "autoqa" or "test-report")

### Artifact Location

The artifact should be placed in the workflow artifacts root directory.

### Expected Path

When downloaded, the artifact should contain a JUnit XML file at one of the following paths:
- `autoqa-test-report.xml`
- `artifacts/autoqa/autoqa-test-report.xml`
- Any `.xml` file within the artifact ZIP

### JUnit XML Format

The JUnit XML must follow the standard JUnit XML format:

```xml
<testsuites>
  <testsuite name="autoqa" tests="5" failures="1" time="2.5">
    <testcase classname="test_module" name="test_function_name" time="0.5">
      <!-- If test passed, no child elements -->
      <!-- If test failed -->
      <failure message="Test failed" type="AssertionError">Error details here</failure>
    </testcase>
    <testcase classname="test_module" name="test_another_function" time="0.3">
      <!-- Skipped test -->
      <skipped message="Test skipped"/>
    </testcase>
  </testsuite>
</testsuites>
```

### Required Fields

Each `<testcase>` element must have:
- `name`: Test name (must match test manifest entry)
- `classname`: Test class/module name (optional but recommended)
- `time`: Test duration in seconds (optional but recommended)

For failed tests:
- `<failure>` element with error message

For skipped tests:
- `<skipped>` element with skip message

## Workflow Integration

### Trigger

Workflows can be triggered via:
1. Workflow dispatch with AutoQA manifest as input
2. PR events (opened, synchronize)
3. Manual trigger

### Manifest Input

When triggered via workflow dispatch, the manifest will be provided as a JSON string in the `manifest` input parameter.

### Example Workflow

```yaml
name: AutoQA Tests

on:
  workflow_dispatch:
    inputs:
      manifest:
        description: 'Test manifest JSON'
        required: true

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run tests
        run: |
          # Parse manifest and run tests
          # Generate JUnit XML output
          pytest --junitxml=autoqa-test-report.xml
      
      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: autoqa-test-report
          path: autoqa-test-report.xml
```

## Parsing and Mapping

AutoQA will:
1. Download the artifact from the workflow run
2. Extract the JUnit XML file
3. Parse test results
4. Map test results to checklist items via:
   - Explicit checklist IDs in manifest
   - Fuzzy matching on test names and checklist descriptions
5. Generate compliance report

## Status Reporting

After processing, AutoQA will:
- Post a PR comment with the compliance report
- Update PR validation status
- Optionally trigger auto-merge if all required items pass

## Error Handling

If the artifact is missing or malformed:
- AutoQA will log an error
- Post a comment on the PR indicating the failure
- Set PR validation status to "error"

