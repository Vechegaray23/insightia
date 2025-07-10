# Cloudflare R2 Module

This Terraform module provisions two Cloudflare R2 buckets named `audio` and `exports`.
Objects in each bucket are encrypted using a customer managed KMS key and are set
to expire after 90 days.

## Usage

```hcl
module "cloudflare_r2" {
  source = "./modules/cloudflare_r2"

  api_token  = var.cloudflare_api_token
  account_id = var.cloudflare_account_id
  kms_key_id = var.r2_kms_key_id
}
```

The module expects a Cloudflare API token with permissions to manage R2 buckets
and a KMS key ID for server‑side encryption. After 90 days, objects are automatically deleted
from both buckets.
