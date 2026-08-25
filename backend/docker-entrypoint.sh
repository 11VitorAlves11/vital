#!/bin/sh
# The API must never come up against an out-of-date schema: migrate first, then
# hand over to the CMD. The catalogue itself is seeded on application startup.
set -e

alembic upgrade head

exec "$@"
