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

## Severity routing

| Incoming `severity` | Default receiver | Use |
| --- | --- | --- |
| `critical` | `primary-oncall` | Page the primary responder |
| `warning` | `team-triage` | Queue an issue for team review |
| `info` | `service-inbox` | Record informational notifications |
| Missing or unknown | `unclassified` | Review mislabelled alerts |

Severity matching is exact and case-sensitive. A matching alert goes to one
receiver. Alertmanager groups by alert name, service and severity. Recovery
notifications use the same receiver as the original alert. The runtime webhook
behind each receiver decides how to deliver the notification.

The output contains complete Alertmanager routing and receiver sections.
Render it through a local plan without applying infrastructure or writing
Terraform state.

```sh
terraform plan -refresh=false -input=false -out=alertmanager.tfplan
terraform show -json alertmanager.tfplan \
  | jq -r '.planned_values.outputs.alertmanager_yaml.value' \
  > alertmanager.generated.yml
amtool check-config alertmanager.generated.yml
amtool config routes test --config.file=alertmanager.generated.yml \
  --verify.receivers=primary-oncall severity=critical
```

Set `destinations` to a map of receiver names to absolute webhook URL files.
Mount those files on the Alertmanager host with access restricted to the
service account. Each file contains the endpoint for that receiver.
Set `severity_destinations` and `fallback_destination` to the names you want
to use. Review the rendered configuration and test the fallback before loading
it into Alertmanager.

[Alertmanager configuration reference](https://prometheus.io/docs/alerting/latest/configuration/)

## Licensing

[MIT](LICENSE).
