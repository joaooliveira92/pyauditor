# Review checklist

## Correctness
- Triggers match intended branches, tags, and paths.
- Job dependencies and conditions cannot skip required gates.
- Python/tool versions match project metadata.
- Install, test, build, and deploy commands match the repository.
- Artifact names and paths are unique and deterministic.

## Security
- Explicit least-privilege permissions.
- Third-party actions pinned to full SHAs.
- No secrets available to untrusted code.
- OIDC limited to deployment/publishing job.
- Protected environments used for sensitive operations.
- User inputs are allowlisted before shell interpolation.
- No dangerous `pull_request_target` checkout pattern.

## Reliability
- Timeouts configured.
- Concurrency set for CI cancellation or serialized deployment.
- Cache keys include lockfiles and runtime version.
- Build artifacts are immutable and promoted rather than rebuilt.
- Deployment has health verification and rollback instructions.

## Maintainability
- Jobs and steps have meaningful names.
- Repeated organization logic is reusable.
- Comments explain constraints, not obvious syntax.
- Dependabot or Renovate updates actions and dependencies.

## Validation report
- Commands executed are listed.
- Exit codes and failures are reported honestly.
- Repository settings and required secrets/variables are documented.
- Residual risks and Conventional Commit message are included.
