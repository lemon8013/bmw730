## start-all.ps1

Starts the three VCTN dev processes detached from the calling shell.

Each process writes its stdout/stderr to logs/dev-<name>.log under this file's
directory. Use scripts/status-all.ps1 to check them and scripts/stop-all.ps1 to
shut them down.

    powershell -ExecutionPolicy Bypass -File scripts/start-all.ps1

## build-frontends.sh

Production build for all four frontends (admin / tools / blog / ops). Each
`npm run build` runs `vue-tsc` first, so a type error fails the build instead
of shipping. Output lands in `dist/web/<app>` plus a `BUILD-REPORT.txt`.

    ./scripts/build-frontends.sh                  # all four, /api/v1 baked in
    ./scripts/build-frontends.sh --app ops        # one
    ./scripts/build-frontends.sh --install        # npm ci first (fresh box / CI)
    ./scripts/build-frontends.sh --archive        # + per-app tar.gz and one bundle

    VITE_API_BASE_URL=https://api.example.com/api/v1 ./scripts/build-frontends.sh

Keep the default `/api/v1`: it is what lets nginx proxy `/api/` on the same
origin. An absolute URL is a cross-origin deploy and needs `CORS_ORIGINS` set
on the backend as well.
