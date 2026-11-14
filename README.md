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

## Escalation and schedules

Render the example with the same local plan workflow. Copy the example before
substituting team-specific responder IDs or coverage dates.

```sh
terraform plan -refresh=false -input=false \
  -var-file=rotations/example.tfvars.example -out=oncall.tfplan
terraform show -json oncall.tfplan \
  | jq '.planned_values.outputs | {oncall_schedules, escalation_policies}'
```

Each rotation starts at a UTC timestamp and cycles through responder IDs in the
listed order for a finite number of fixed-duration shifts. A shift includes
its start and excludes its end. That assigns the handoff instant to the
incoming responder. The example dates are synthetic. Set the anchor and shift
count for the period you intend to cover. Fixed UTC shifts keep their elapsed
duration across daylight saving changes, so local wall-clock handoff times
can move.

A policy belongs to an Alertmanager receiver. Start with a rotation at minute
zero and add another at a later offset from the initial notification. A
notification consumer should look up the responder at each scheduled
escalation time, stop when the alert is acknowledged or resolved, and treat
missing coverage as an operational error. Terraform exports the policy and
handoff windows. The webhook consumer owns timers and acknowledgement state.
Receivers without a policy continue to use the existing routing configuration.

## Licensing

[MIT](LICENSE).
