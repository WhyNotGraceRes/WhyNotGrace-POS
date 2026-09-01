#!/bin/sh
# Run via the OS's own shebang handling (not an inline shell string passed
# through a platform's "command override" field) so migrate-then-serve is
# reliable everywhere, regardless of whether that field actually invokes a
# real shell — see render.yaml's history for why this matters: Render's
# dockerCommand ran an inline "a && b" string as one literal (non-existent)
# command instead of two sequential ones.
set -e
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
