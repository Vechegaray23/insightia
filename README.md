# Proyecto Insightia

## Project Structure

- iac/: Infrastructure as code (Terraform/Pulumi)
- backend/: API implementation
- frontend/: Web or mobile app

### IAC Modules

- `modules/supabase`: Terraform module to provision a Supabase project with database and authentication enabled.
- `modules/cloudflare_r2`: Terraform module to provision Cloudflare R2 buckets for audio and exports with KMS encryption and 90-day retention.
- `modules/render`: Terraform module to deploy a simple Render container service named `hello`.

## Development

This repository uses **pre-commit** hooks for code formatting and linting.
Install the hooks after cloning:

```bash
pre-commit install --install-hooks
```

The configured hooks run **black**, **ruff**, **terraform fmt**, and enforce
conventional commit messages with **gitlint**.
