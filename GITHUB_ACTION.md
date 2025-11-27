# GitHub Action Usage

This repository can be used as a GitHub Action to convert CGMES RDF schemas to JSON-LD context files in your CI/CD pipeline.

## Quick Start

Add this to your workflow file (e.g., `.github/workflows/convert-schemas.yml`):

```yaml
name: Convert CGMES Schemas

on:
  push:
    paths:
      - 'cgmes-data/**'
  workflow_dispatch:

jobs:
  convert:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Convert RDF schemas to JSON-LD
        uses: your-username/cgmes-cim16-jsonld@main
        with:
          schema-dir: 'cgmes-data'
          output-dir: 'output'
          context-base-url: 'https://example.com/contexts'

      - name: Upload generated contexts
        uses: actions/upload-artifact@v4
        with:
          name: jsonld-contexts
          path: output/
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `schema-dir` | Directory containing RDF schema files (.rdf, .ttl) | Yes | `cgmes-data` |
| `output-dir` | Output directory for JSON-LD context files | Yes | `output` |
| `base-uri` | Base URI for CIM classes | No | `http://iec.ch/TC57/2013/CIM-schema-cim16#` |
| `context-base-url` | Base URL where context files will be hosted (enables absolute URLs) | No | `''` (uses relative URLs) |

## Outputs

| Output | Description |
|--------|-------------|
| `context-file` | Path to the generated main context.jsonld file |
| `class-count` | Number of classes generated |
| `property-count` | Number of properties extracted |

## Examples

### Basic Usage

```yaml
- name: Convert schemas
  uses: your-username/cgmes-cim16-jsonld@main
  with:
    schema-dir: 'schemas'
    output-dir: 'dist/contexts'
```

### With Absolute URLs for CDN

```yaml
- name: Convert schemas with CDN URLs
  uses: your-username/cgmes-cim16-jsonld@main
  with:
    schema-dir: 'cgmes-data'
    output-dir: 'output'
    context-base-url: 'https://cdn.example.com/cim/v2'
```

### Deploy to GitHub Pages

Complete workflow to convert and deploy to GitHub Pages:

```yaml
name: Convert and Deploy to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  convert-and-deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Convert RDF schemas to JSON-LD
        id: convert
        uses: your-username/cgmes-cim16-jsonld@main
        with:
          schema-dir: 'cgmes-data'
          output-dir: 'public'
          context-base-url: 'https://your-username.github.io/your-repo'

      - name: Show conversion statistics
        run: |
          echo "Generated ${{ steps.convert.outputs.class-count }} classes"
          echo "Extracted ${{ steps.convert.outputs.property-count }} properties"
          echo "Context file: ${{ steps.convert.outputs.context-file }}"

      - name: Setup Pages
        uses: actions/configure-pages@v4

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: 'public'

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

### Custom Base URI

```yaml
- name: Convert with custom base URI
  uses: your-username/cgmes-cim16-jsonld@main
  with:
    schema-dir: 'schemas'
    output-dir: 'output'
    base-uri: 'http://mycompany.com/cim#'
    context-base-url: 'https://mycompany.com/contexts'
```

### Deploy to S3/CloudFront

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  convert-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Convert schemas
        uses: your-username/cgmes-cim16-jsonld@main
        with:
          schema-dir: 'cgmes-data'
          output-dir: 'dist'
          context-base-url: 'https://d1234567890.cloudfront.net'

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Deploy to S3
        run: |
          aws s3 sync dist/ s3://my-bucket/contexts/ --delete
          aws cloudfront create-invalidation --distribution-id E1234567890 --paths "/*"
```

## Local Testing

You can test the action locally using [act](https://github.com/nektos/act):

```bash
# Install act
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run the action locally
act -j convert
```

## Development

To use this action from a local path during development:

```yaml
- name: Convert schemas
  uses: ./  # Use current repository
  with:
    schema-dir: 'cgmes-data'
    output-dir: 'output'
```

## Output Structure

After running the action, the output directory will contain:

```
output/
├── context.jsonld          # Main entrypoint context
└── CIM/
    ├── ACDCConverter.jsonld
    ├── Terminal.jsonld
    └── ... (180+ class contexts)
```

## Notes

- The action uses Python 3.13 and [uv](https://github.com/astral-sh/uv) for dependency management
- All generated files use UTF-8 encoding
- The action is stateless and can be run multiple times safely
- Output files are ready for immediate deployment to static hosting
