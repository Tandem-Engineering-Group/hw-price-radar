# Kickoff — paste this into Claude Code

> Read lakehouse/CLAUDE.md end to end, then read every file under lakehouse/.
> Confirm the phase plan back to me in one short list, then execute **Phase 0** and
> **Phase 1** only. STOP at every gate as written. Do not touch adapters or the cron
> until their phases. Run pytest (from `lakehouse/`) before and after any change to src/.

Repo setup: none — this section already lives inside
`Tandem-Engineering-Group/hw-price-radar` under `lakehouse/` (project) and
`site/lakehouse/` (public portal). When the project outgrows the host repo, migration
is a directory move into a fresh repo plus a workflow copy; nothing in here may
reference hw-price-radar paths outside these two directories.
