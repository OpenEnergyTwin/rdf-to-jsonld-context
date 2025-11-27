# Workflow Examples

This directory contains example workflows for using the CGMES JSON-LD converter action.

## Files

- **`example.yml`** - Basic example showing how to use the action

## Quick Start

### Option 1: Use as GitHub Action

```yaml
- uses: your-username/cgmes-cim16-jsonld@main
  with:
    schema-dir: 'cgmes-data'
    output-dir: 'output'
    context-base-url: 'https://example.com/contexts'
```

### Option 2: Run locally in workflow

```yaml
- uses: actions/checkout@v4

- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.13'

- name: Install uv and run converter
  run: |
    curl -LsSf https://astral.sh/uv/install.sh | sh
    uv sync
    uv run python main.py cgmes-data output \
      --context-base-url "https://example.com/contexts"
```

## Customization

Copy `example.yml` and modify:
- Trigger conditions (`on:`)
- Input directories
- Output configuration
- Deployment targets

For full documentation, see [GITHUB_ACTION.md](../../GITHUB_ACTION.md)
