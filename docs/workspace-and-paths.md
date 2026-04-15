# Workspace and paths

## Path precedence

Repository and workspace paths are resolved in this order:

1. CLI-provided path overrides (when supplied)
2. environment variables (`MERIDIAN_REPO_PATH`, `MERIDIAN_AUX_REPO_PATH`, `MERIDIAN_EXPERT_WORKSPACE`)
3. `config/repos.local.yaml`
4. `config/repos.example.yaml`
5. fallback defaults (`../meridian`, `../meridian_aux`, `./runtime`)

## Runtime expectation: local sibling repositories

For real investigations, `meridian_expert` expects directory-based local sibling repositories:

- `../meridian`
- `../meridian_aux`

The `doctor` command reports each repo's configured path, existence, git availability, and whether the environment is ready for real investigation.

## What happens when repos are missing

If a task reaches investigation and required sibling repos are missing, the run is blocked and an investigation blocker artifact is written under the task cycle. The artifact explains that local sibling repositories are required and lists missing repos.

This preserves deterministic behavior while preventing false confidence from pretending a real cross-repo read happened.

## Fixture repositories in tests and demos

In Codex and CI-oriented tests, behavior is validated with synthetic fixture repositories (not real Meridian checkouts):

- fixture repos are generated under temp paths
- `MERIDIAN_REPO_PATH` and `MERIDIAN_AUX_REPO_PATH` are set to fixture directories
- `MERIDIAN_EXPERT_LLM_BACKEND=fake` keeps model behavior deterministic and offline

This is intentional and does not change runtime design: humans can later point the same system at real local siblings.

## Workspace tree

Runtime artifacts are rooted at `MERIDIAN_EXPERT_WORKSPACE` (default `./runtime`) and include:

- `tasks/<task_id>/input`
- `tasks/<task_id>/cycles/<cycle_id>/(triage|investigation|draft|review)`
- `tasks/<task_id>/cycles/<cycle_id>/prototype/...` (prototype namespacing)
- `tasks/<task_id>/deliveries/` and `tasks/<task_id>/deliveries/prototype/`
- `meridian_expert.db` SQLite store at workspace root
