# Operations Runbook

## Deploy

1. Ensure `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` GitHub Action secrets are set.
2. Push to `main` or run the Deploy workflow manually.
3. Verify service readiness:
   - `GET /ready` on ports 5001-5004

## Rollback

1. SSH into the VM.
2. In `/opt/devops-lab`, reset to a known-good commit:
   - `git reset --hard <commit_sha>`
3. Restart:
   - `docker compose up -d --build`

## Incident response (baseline)

1. Check container status: `docker compose ps`
2. Check logs: `docker compose logs <service>`
3. Check readiness endpoint for failed service.
4. If database issue, restart postgres and validate `pg_isready`.

## Backup and restore (baseline)

- Backup: `pg_dump -U devops devops_lab > backup.sql`
- Restore: `psql -U devops devops_lab < backup.sql`
