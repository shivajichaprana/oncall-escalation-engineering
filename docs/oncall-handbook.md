# On-call handbook

This repository provides a local workflow for reviewing routes, schedules,
alert quality, and shift handoff context. Use synthetic data for demonstrations.
Keep real incident exports and reports in the team's protected workspace.

## Review a routing change

1. Check the source alert's labels and the intended receiver. Include a
   fallback receiver with an owner who can investigate unrecognised severities.
2. Set the receiver URL file paths in a private variable file. Review the
   runtime webhook destinations and their ability to deliver resolved events.
3. Run `make validate` and `make simulate`. The latter requires `terraform`
   and `amtool` on PATH and runs the routing cases with Alertmanager itself.
4. Run `make deploy VAR_FILE=/path/to/reviewed.tfvars OUTPUT=/path/to/alertmanager.yml`
   to stage a validated local configuration file. The default inputs use the
   synthetic rotation example and the default output is `build/alertmanager.yml`.
5. Compare the staged artifact with the currently used configuration. The team
   managing Alertmanager controls the service reload and operational checks.
   Preserve the previous configuration for recovery.

The `deploy` target prepares the local artifact through a Terraform plan,
extracts the YAML, validates it with `amtool`, and replaces the output only
after successful validation. The file contains paths to runtime webhook URL
files. Verify those files and their delivery endpoints in the intended runtime.

## Review coverage and escalations

Choose a UTC anchor and a finite coverage horizon. Confirm every responder is
available and that escalation rotations have coverage at the times they may
be invoked. Review all offsets from the initial notification, including
behaviour when an acknowledgement or resolution arrives before the next step.

The [example rotation file](../rotations/example.tfvars.example) demonstrates
the input shape with synthetic IDs and dates. Replace those values for the
period being reviewed. Use the [handoff export workflow](../README.md#capture-a-shift-handoff)
to inspect a boundary. Review warnings for gaps, missing incident owners, and
missing next actions before accepting a handoff.

A report uses the supplied local incident snapshot. Its capture timestamp and
age show how current that snapshot is at the requested handoff time. Confirm
the source system's current incident state before acting on old context.
Assign an owner and a next action for unresolved work and record the handoff
acceptance in the team's existing incident system.

## Review alert quality

Export distinct occurrences after grouping repeated firings. Preserve the
observation window and selection method with the export. Review
`incident_confirmed` and `action_required` independently using explicit
`true`, `false`, or `null` judgements.

Precision measures confirmed incidents among reviewed occurrences.
Actionability measures useful interventions among reviewed occurrences.
Unknown values remain outside each rate's denominator and appear in its
coverage figures. An empty review produces a null rate. A low coverage figure
is a reason to collect more evidence before drawing conclusions about a rule.

Run `python3 -m quality.report quality/example.json` to inspect a synthetic
report. Compare counts and coverage alongside rates. Global rates are weighted
by occurrence counts. These exports alone cannot establish recall because they
contain no evidence about incidents that generated no alert.

## Validation failures

- If a Terraform input check fails, correct the named receiver, rotation, delay,
  or time window and regenerate the plan.
- If routing resolves unexpectedly, inspect label spelling, case, and the
  custom mapping before changing the fallback.
- If `amtool` rejects a generated file, preserve the working runtime
  configuration and fix the candidate before staging it again.
- If report parsing fails, check the documented JSON fields, duplicate IDs,
  timezone offsets, and the snapshot capture time.

CI covers Terraform policy checks, Python tests on 3.10 and 3.13, and a
dedicated routing job with checksum-verified Alertmanager tooling. The final
`ci-complete` job succeeds when every required job passes.
