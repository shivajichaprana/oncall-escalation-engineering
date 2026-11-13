# On-call escalation engineering

Terraform configuration for alert routing, escalation policy, alert-quality
scoring, and shift handoffs. The Terraform root runs locally with no cloud
provider, backend configuration, or external credentials.

## Validate locally

With Terraform 1.6 or newer, run these commands from the repository root.

```sh
terraform init -backend=false -input=false
terraform fmt -check -recursive
terraform validate
terraform test
```

The test suite uses plan-only runs. GitHub Actions runs the same validation
commands and exposes the result through the `ci-complete` check.

## Licensing

[MIT](LICENSE).
