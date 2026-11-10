#!/usr/bin/env python3
"""
Gathers system-health signals for the OK040 homepage's "System status"
section and writes them to /volume1/web/status.json for the static page
to fetch() client-side.

Must run as root — needs the docker socket (container inspect + watchtower
log) and full read access to backup/security-scan state. Runs via DSM
Task Scheduler (Control Panel -> Task Scheduler -> User-defined script,
run as: root). Safe to re-run anytime; never raises, always writes a
best-effort JSON file with "unknown" for anything it couldn't determine.

Known limitation (2026-09-08): the per-container "update_available" field
comes from grepping watchtower's own log output, which was written
without being able to test against real `docker logs watchtower` output
(no root/docker access in the session that wrote this script). If that
field stays "unknown" for everything once this has run for real, the
regexes in containers_status() need a look at the actual log format.
"""
import json
import os
import re
import subprocess
from datetime import datetime, timezone

OUT_PATH = "/volume1/web/status.json"

TM_SPARSEBUNDLE = "/volume1/timemachine/joost.sparsebundle"

# Weekly LinkedIn database backups pushed from the Mac (see host README, "Mac
# project backups"). Each backup is a directory named by its UTC creation time;
# it only appears once complete (the Mac renames it into place after verifying).
LINKEDIN_BACKUP_DIR = "/volume1/backup/linkedin-archive"

# Hyper Backup's local per-repo cache dirs; their mtime tracks the last
# time that repo was touched by a backup run. This is a recency proxy,
# not a confirmed pass/fail result from OK035 itself -- Hyper Backup's
# actual per-run result history lives in a root-only store we didn't
# find a stable, documented way to read from a script.
HB_REPO_CACHES = {
    "Media Docker (Backup C)": "/volume1/@img_bkp_cache/ClientCache_image_image_remote.dmLRJx",
    "Backup D": "/volume1/@img_bkp_cache/ClientCache_image_image_remote.1gUao7",
}

SECURITYSCAN_RESULT = "/var/lib/securityscan/securityscanResult.json"

def now():
    return datetime.now(timezone.utc)


def iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def age_days(ts):
    return (now().timestamp() - ts) / 86400


def parse_docker_ts(ts):
    """Parse a Docker-supplied RFC3339 timestamp.

    Docker reports timestamps (container Created, and this watchtower
    fork's log lines) with nanosecond precision -- up to 9 fractional
    digits, e.g. "2026-09-02T19:29:05.964720949Z". Python 3.8's
    datetime.fromisoformat only accepts up to 6, so truncate first.
    """
    ts = ts.replace("Z", "+00:00")
    ts = re.sub(r"(\.\d{6})\d+", r"\1", ts)
    return datetime.fromisoformat(ts)


def run(cmd, timeout=20):
    # docker keeps stdout/stderr as separate streams; `docker logs` in
    # particular writes container output to whichever stream the
    # container itself wrote to (watchtower, like most Go/logrus apps,
    # writes to stderr). A terminal shows both interleaved, which hid
    # this bug during manual testing -- merge them here so nothing is
    # silently dropped.
    try:
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        ).stdout
    except Exception:
        return ""


def time_machine():
    try:
        mtime = os.path.getmtime(TM_SPARSEBUNDLE)
    except OSError:
        return {"status": "unknown"}
    days = age_days(mtime)
    status = "ok" if days <= 7 else ("warn" if days <= 9 else "stale")
    return {"last_backup": iso(mtime), "age_days": round(days, 1), "status": status}


def linkedin_backup():
    """Age of the newest complete LinkedIn backup. The Mac job runs hourly but
    only creates a backup when the newest is over 7 days old, so a healthy
    system is never much older than 8 days; beyond that the job has stopped
    or the NAS copy is failing, which nothing else would announce."""
    newest = None
    try:
        names = os.listdir(LINKEDIN_BACKUP_DIR)
    except OSError:
        return {"status": "unknown"}
    for name in names:
        try:
            created = datetime.strptime(name, "%Y-%m-%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue  # skips .tmp-* in-progress copies and anything else
        if not os.path.isfile(os.path.join(LINKEDIN_BACKUP_DIR, name, "MANIFEST.json")):
            continue
        if newest is None or created > newest:
            newest = created
    if newest is None:
        return {"status": "stale", "note": "no backup found"}
    days = (now() - newest).total_seconds() / 86400.0
    status = "ok" if days <= 8 else ("warn" if days <= 9 else "stale")
    return {"last_backup": newest.isoformat(), "age_days": round(days, 1), "status": status}


def ok035_backup():
    repos = {}
    worst = "ok"
    order = {"ok": 0, "warn": 1, "stale": 2, "unknown": 1}
    for label, path in HB_REPO_CACHES.items():
        try:
            mtime = os.path.getmtime(path)
            days = age_days(mtime)
            status = "ok" if days <= 8 else ("warn" if days <= 10 else "stale")
        except OSError:
            mtime, days, status = None, None, "unknown"
        repos[label] = {
            "last_activity": iso(mtime) if mtime else None,
            "age_days": round(days, 1) if days is not None else None,
            "status": status,
        }
        if order[status] > order[worst]:
            worst = status
    return {
        "repos": repos,
        "status": worst,
        "note": "based on local backup-cache activity, not a confirmed remote result",
    }


def security_advisor():
    try:
        with open(SECURITYSCAN_RESULT) as f:
            data = json.load(f)
    except Exception:
        return {"status": "unknown"}
    updates = []
    fail = warn = 0
    for rule in data.values():
        u = rule.get("update")
        try:
            if u:
                updates.append(int(u))
        except (TypeError, ValueError):
            pass
        if rule.get("status") == "fail":
            # Synology's own severities, seen in practice: info, warning,
            # risk, danger, outOfDate. Only the genuinely serious ones
            # count as "fail" (red); info/warning/outOfDate are real but
            # lower-priority, so they land in the amber bucket instead.
            if rule.get("severity") in ("danger", "risk"):
                fail += 1
            else:
                warn += 1
    if not updates:
        return {"status": "unknown"}
    last = max(updates)
    days = age_days(last)
    # Two independent things determine the color: is the scan itself
    # fresh, and did it actually find problems. A scan that ran an hour
    # ago with real failures is not "ok" just because it's recent --
    # take the worse of the two ("stale" is this shared vocabulary's
    # top/red tier across every card, not literally about data age here).
    recency_status = "ok" if days <= 14 else ("warn" if days <= 30 else "stale")
    if fail > 0:
        findings_status = "stale"
    else:
        # Plain warning/info findings (e.g. default DSM ports, HTTPS
        # redirect off) are expected on a Tailscale-only NAS and cannot
        # be cleared without changing deliberate settings, so they stay
        # green and are only reported via warning_count. Only risk/danger
        # findings (fail > 0) or an old scan change the color.
        findings_status = "ok"
    severity = {"ok": 0, "warn": 1, "stale": 2}
    status = max(recency_status, findings_status, key=severity.get)
    return {
        "last_scan": iso(last),
        "age_days": round(days, 1),
        "fail_count": fail,
        "warning_count": warn,
        "status": status,
    }


def watchtower_run_and_log():
    log = run(["docker", "logs", "--since", "48h", "watchtower"])
    # Real format (confirmed against nicholas-fedor/watchtower 1.22.0,
    # 2026-09-08): `time=2026-09-05T15:24:35+02:00 level=info
    # msg="Update session completed" failed=0 notify=no scanned=1
    # skipped=0 updated=0` -- no quotes around the timestamp.
    sessions = re.findall(
        r'time=(\S+)[^\n]*msg="Update session completed"'
        r'[^\n]*\bfailed=(\d+)[^\n]*\bscanned=(\d+)'
        r'[^\n]*\bskipped=(\d+)[^\n]*\bupdated=(\d+)',
        log,
    )
    if not sessions:
        # No completed "Update session" line yet (e.g. just redeployed,
        # first cycle hasn't run) -- there's a container-start timestamp
        # to show, but no real check has actually completed, so this is
        # honestly "unknown", not "ok". Showing green here from nothing
        # but log activity is exactly the same mistake as the Security
        # Advisor recency-vs-findings bug -- don't repeat it.
        times = re.findall(r"time=(\S+)", log)
        if not times:
            return {"status": "unknown"}, log
        try:
            last = parse_docker_ts(times[-1])
        except ValueError:
            return {"status": "unknown"}, log
        return {
            "last_seen_log": last.isoformat(),
            "status": "unknown",
            "note": "container is up but hasn't completed a check cycle yet",
        }, log
    ts, failed, scanned, skipped, updated = sessions[-1]
    try:
        last = parse_docker_ts(ts)
    except ValueError:
        return {"status": "unknown"}, log
    hrs = (now() - last).total_seconds() / 3600
    status = "ok" if hrs <= 12 else ("warn" if hrs <= 24 else "stale")
    if int(failed) > 0:
        status = "warn" if status == "ok" else status
    return {
        "last_run": last.isoformat(),
        "age_hours": round(hrs, 1),
        "scanned": int(scanned),
        "skipped": int(skipped),
        "updated": int(updated),
        "failed": int(failed),
        "status": status,
    }, log


def normalize_container_name(name):
    """Normalize Docker inspect/watchtower names to their bare container name."""
    if not isinstance(name, str):
        return ""
    return name.lstrip("/")


def parse_update_flags(watchtower_log):
    """Map normalized container names to Watchtower update availability."""
    flags = {}
    for name, equal in re.findall(
        r'msg="Categorizing container status" container=(\S+) images_equal=(true|false)',
        watchtower_log,
    ):
        flags[normalize_container_name(name)] = equal == "false"
    return flags


def watchtower_scope():
    """Names Watchtower was told to watch, or None if that can't be read."""
    try:
        data = json.loads(run(["docker", "inspect", "watchtower"]))[0]
        command = data.get("Config", {}).get("Cmd") or []
        return set(normalize_container_name(name) for name in command)
    except Exception:
        return None


def containers_status(watchtower_log):
    """Discover all containers, including stopped ones, and inspect runtime state."""
    try:
        listing = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.ID}} {{.Names}}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20,
        )
    except Exception:
        return [], {"status": "unavailable", "message": "Docker container listing failed"}
    if listing.returncode != 0:
        return [], {"status": "unavailable", "message": "Docker container listing failed"}

    entries = []
    seen = set()
    lines = listing.stdout.splitlines()
    for line in lines:
        fields = line.split(None, 1)
        if len(fields) != 2 or not fields[0].strip() or not fields[1].strip():
            return [], {"status": "unavailable", "message": "Docker container listing was malformed"}
        container_id, listed_name = fields[0].strip(), normalize_container_name(fields[1].strip())
        if container_id in seen:
            continue
        seen.add(container_id)
        entries.append((container_id, listed_name))
    if not entries:
        if lines:
            return [], {"status": "unavailable", "message": "Docker container listing was malformed"}
        return [], {"status": "empty", "message": "No Docker containers found"}

    update_flags = parse_update_flags(watchtower_log)
    scope = watchtower_scope()
    out = []
    inspect_errors = 0
    for container_id, listed_name in entries:
        raw = run(["docker", "inspect", container_id])
        try:
            inspected = json.loads(raw)
            if not isinstance(inspected, list) or len(inspected) != 1 or not isinstance(inspected[0], dict):
                raise ValueError("invalid inspect response")
            data = inspected[0]
        except Exception:
            inspect_errors += 1
            out.append({
                "name": listed_name,
                "runtime_state": "unknown",
                "update_available": update_flags.get(listed_name),
                "update_policy": None if scope is None else ("watchtower" if listed_name in scope else "manual"),
            })
            continue

        name = normalize_container_name(data.get("Name")) or listed_name
        state = data.get("State")
        running = state.get("Running") if isinstance(state, dict) else None
        runtime_state = "running" if running is True else ("stopped" if running is False else "unknown")
        config = data.get("Config")
        image = config.get("Image", "") if isinstance(config, dict) else ""
        created = data.get("Created")
        days_old = None
        if created:
            try:
                created_ts = parse_docker_ts(created).timestamp()
                days_old = round(age_days(created_ts), 1)
            except (ValueError, TypeError):
                pass
        item = {
            "name": name,
            "runtime_state": runtime_state,
            "image": image,
            "created": created,
            "age_days": days_old,
            "update_available": update_flags.get(name),
            "update_policy": None if scope is None else ("watchtower" if name in scope else "manual"),
        }
        if runtime_state == "running" and isinstance(state.get("StartedAt"), str):
            try:
                started = parse_docker_ts(state["StartedAt"])
                minutes = max(0, int((now() - started).total_seconds() // 60))
                item["runtime_label"] = "Up for {} mins".format(minutes)
            except (ValueError, TypeError):
                item["runtime_label"] = "Running"
        elif runtime_state == "stopped":
            item["runtime_label"] = "Stopped"
        else:
            item["runtime_label"] = "Runtime state unknown"
        out.append(item)

    collection_status = "partial" if inspect_errors else "available"
    collection = {"status": collection_status, "message": "{} container(s) found".format(len(out))}
    if inspect_errors:
        collection["inspect_errors"] = inspect_errors
    return out, collection


def main():
    wt_status, wt_log = watchtower_run_and_log()
    containers, container_collection = containers_status(wt_log)
    result = {
        "generated_at": now().isoformat(),
        "time_machine": time_machine(),
        "linkedin_backup": linkedin_backup(),
        "ok035_backup": ok035_backup(),
        "security_advisor": security_advisor(),
        "watchtower": wt_status,
        "containers": containers,
        "container_collection": container_collection,
    }
    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(result, f, indent=2)
    os.replace(tmp, OUT_PATH)
    os.chmod(OUT_PATH, 0o644)


if __name__ == "__main__":
    main()
