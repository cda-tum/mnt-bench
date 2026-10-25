# Controlled server upgrades

Publishing to PyPI and copying `mntbench_version.txt` do **not** prove that the hosted process was upgraded.
The release workflow only sends that notification. Deployment remains an explicit administrator operation.

The application now provides:

- `mnt.bench.main:create_app(...)`: a Gunicorn/WSGI factory that does not start Flask's development server.
- `GET /mntbench/health`: HTTP 200 and `{"status":"ready","version":"..."}` when the library is initialized,
  otherwise HTTP 503. The version is captured during startup, so upgrading files without restarting cannot
  falsely report a new running version. Responses must not be cached by the reverse proxy.

## Prerequisites

Use a release containing the factory and health endpoint. Older releases, including 0.4.2, do not contain them.
Use uv 0.13.5 or newer; keep the host's CA store patched. Python 3.10 reached upstream end of life on
[October 1, 2026](https://devguide.python.org/versions/). A uv-managed Python 3.13 lets this service migrate
without replacing Ubuntu's system Python. Package support for 3.10 remains until the server migration is confirmed.

Review `systemctl cat mntbench` and adapt the example unit's user, group, paths, and port to the actual host.
The example uses `web-user`, port 8000, and the existing archive at `/local/mntbench/fgl_output/`.
The service account must be able to read the archive and interpreter and write its download log.
Keep the reverse proxy configuration, archive, and existing environment. Never install or upgrade packages at service startup.
If the old `start.sh` contains `pip install -U`, back it up and remove that installation line before the migration:
otherwise restoring the old service could immediately upgrade the rollback environment again.
Each worker opens its own archive; the sample intentionally does not use Gunicorn's `--preload`.
This procedure assumes unchanged benchmark data. If a release changes the archive checksum, use a separate data
directory for the candidate and keep the old archive for rollback; update both the preflight command and the new unit.

## Prepare and test before switching

Run the following in **Bash** as an administrator, from a checkout of the release.
Choose an unused loopback port for the candidate (5058 below), and replace `X.Y.Z` with the exact published version.

```bash
bash
set -euo pipefail
VERSION=X.Y.Z
root=/var/www/cda/app/mntbench
candidate="$root/releases/$VERSION-$(date +%s)"
export UV_PYTHON_INSTALL_DIR="$root/python"
mkdir -p "$root/releases"
uv python install 3.13
uv venv --managed-python --python 3.13 "$candidate"
uv pip install --python "$candidate" "mnt.bench==$VERSION" gunicorn
uv pip check --python "$candidate"
uv pip freeze --python "$candidate" > "$candidate/installed-requirements.txt"

verify() {
  curl --fail --silent --show-error --retry 20 --retry-all-errors --retry-delay 2 \
    --max-time 5 "$1/mntbench/health" |
    "$candidate/bin/python" -c 'import json, sys; d=json.load(sys.stdin); sys.exit(0 if d == {"status": "ready", "version": sys.argv[1]} else 1)' "$VERSION"
}

sudo -u web-user "$candidate/bin/gunicorn" --bind 127.0.0.1:5058 --workers 1 \
  'mnt.bench.main:create_app(skip_question=True, activate_logging=True, target_location="/local/mntbench/fgl_output/")' &
candidate_pid=$!
trap 'kill "$candidate_pid" 2>/dev/null || true' EXIT
verify http://127.0.0.1:5058
kill "$candidate_pid"
wait "$candidate_pid" || true
trap - EXIT
```

Do not proceed if installation, checksum validation, permissions, or the candidate health check fails.
Check filtering and one small ZIP download through the candidate UI if application behavior changed.

## Switch, verify, and roll back on failure

Keep the same Bash session. This backs up the old unit, retains the old environment, and only replaces a symlink.
For the first migration, `mntbench/` is the existing environment; subsequent upgrades use `current`.
The unit backup also allows rollback to the old `start.sh` service during that first migration.

```bash
previous="$root/mntbench"
if test -L "$root/current"; then previous="$(readlink -f "$root/current")"; fi
test -d "$previous"
test ! -e "$root/current" || test -L "$root/current"
backup="$(mktemp "$root/mntbench.service.XXXXXX")"
cp /etc/systemd/system/mntbench.service "$backup"

switch_environment() {
  ln -s "$1" "$root/current.next" &&
    mv -Tf "$root/current.next" "$root/current"
}

if switch_environment "$candidate" &&
   install -m 644 deploy/mntbench.service /etc/systemd/system/mntbench.service &&
   systemctl daemon-reload &&
   systemctl restart mntbench &&
   verify http://127.0.0.1:8000; then
  systemctl status mntbench --no-pager
else
  cp "$backup" /etc/systemd/system/mntbench.service
  switch_environment "$previous"
  systemctl daemon-reload
  systemctl restart mntbench
  journalctl -u mntbench -n 50 --no-pager
  echo "Upgrade failed; previous unit and environment restored." >&2
  exit 1
fi
```

Finally verify `https://www.cda.cit.tum.de/mntbench/health` and download a small selection through the public site.
Confirm the reported version equals `VERSION`; a copied version file is not evidence of success.
If the reverse proxy check fails, use the rollback commands from the `else` block, then investigate the proxy.
Retain the backup unit and previous environment until this check passes. No archive or environment is deleted by this procedure.
