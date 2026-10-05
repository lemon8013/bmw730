Starts the three VCTN dev processes detached from the calling shell.

Each process writes its stdout/stderr to logs/dev-<name>.log under this file's
directory. Use scripts/status-all.ps1 to check them and scripts/stop-all.ps1 to
shut them down.

    powershell -ExecutionPolicy Bypass -File scripts/start-all.ps1
