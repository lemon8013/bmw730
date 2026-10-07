"""app.ops.scheduler — in-process periodic jobs for the ops platform.

Four jobs, all of them previously configured but never triggered:

* hourly and daily metric rollups (the console reads the rollup tables);
* alert rule evaluation, which is also what dispatches notifications;
* availability probes, which is what turns a check row into observations;
* the retention purge, without which the monitoring tables only ever grow.
"""

from app.ops.scheduler.runtime import OpsScheduler, build_scheduler

__all__ = ["OpsScheduler", "build_scheduler"]
