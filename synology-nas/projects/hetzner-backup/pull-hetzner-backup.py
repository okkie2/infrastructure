#!/usr/bin/env python3
"""Fetch new Hetzner platform backups to OK040, verify every copy, prune, and confirm.

Run daily at 07:30 by DSM Task Scheduler as the unprivileged user `hetznerbackup`.
Source of truth: infrastructure/synology-nas/projects/hetzner-backup/ (see its README).
Python 3.8 compatible (DSM 7.4 ships 3.8); standard library only.

The Hetzner side only answers `list`, `get <stamp> <file>` and `done <stamp>`. This script
chooses every local path itself, never touches a backup it already holds, and treats
everything the server sends as untrusted bytes.
"""
import configparser
import datetime
import fcntl
import hashlib
import json
import os
import pathlib
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import urllib.request

CONF_DIR = pathlib.Path("/usr/local/etc/hetzner-backup")
STAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z", re.ASCII)
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", re.ASCII)
HEX = re.compile(r"[0-9a-f]{64}", re.ASCII)
SUMS = "SHA256SUMS"
REQUIRED = ("globals.sql",)
MAX_SUMS_BYTES = 64 * 1024
RUN_TIMEOUT = 50 * 60  # seconds; the whole run, so a hang still ends in an alert
CALL_TIMEOUT = 15 * 60


class Failure(Exception):
    pass


def log(message):
    print("{} {}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message), flush=True)


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def parse_stamp(name):
    return datetime.datetime.strptime(name, "%Y-%m-%dT%H%M%SZ").replace(tzinfo=datetime.timezone.utc)


def load_config():
    parser = configparser.ConfigParser()
    path = CONF_DIR / "hetzner-backup.conf"
    if not parser.read(str(path)):
        raise Failure("config file missing or unreadable: {}".format(path))
    return parser["pull"]


def ssh_command(conf, request):
    return [
        "/usr/bin/ssh", "-F", "/dev/null", "-i", str(CONF_DIR / "id_ed25519"),
        "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=yes",
        "-o", "HostKeyAlgorithms=ssh-ed25519",  # the pinned key; DSM's ssh 8.2 would otherwise ask for ECDSA
        "-o", "UserKnownHostsFile={}".format(CONF_DIR / "known_hosts"),
        "-o", "ConnectTimeout=20", "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4",
        "{}@{}".format(conf["user"], conf["host"]), request,
    ]


def _keep_tail(stream, keep, out):
    """Drain a stream, keeping only its last `keep` bytes, so a flood cannot fill memory or disk."""
    tail = b""
    for chunk in iter(lambda: stream.read(4096), b""):
        tail = (tail + chunk)[-keep:]
    out.append(tail)


def remote_stream(conf, request, sink, limit):
    """Run one request and pass its output to `sink` in chunks. The call is killed as soon as
    the output exceeds `limit` bytes; only the last 2 KB of stderr are kept."""
    proc = subprocess.Popen(ssh_command(conf, request), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    tail = []
    drain = threading.Thread(target=_keep_tail, args=(proc.stderr, 2048, tail), daemon=True)
    drain.start()
    size = 0
    try:
        for chunk in iter(lambda: proc.stdout.read(1 << 16), b""):
            size += len(chunk)
            if size > limit:
                raise Failure("'{}' returned more than {} bytes".format(request, limit))
            sink(chunk)
        code = proc.wait(timeout=CALL_TIMEOUT)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        drain.join(timeout=5)
    if code != 0:
        message = (tail[0] if tail else b"").decode(errors="replace").strip()[-200:]
        raise Failure("'{}' failed (exit {}): {}".format(request, code, message))


def remote_text(conf, request, limit):
    parts = []
    remote_stream(conf, request, parts.append, limit)
    return b"".join(parts).decode("ascii")


def fetch_file(conf, stamp, name, target, max_bytes):
    """Stream one remote file into a new local file this script names; return its SHA-256."""
    fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    digest = hashlib.sha256()
    with os.fdopen(fd, "wb") as out:
        def sink(chunk):
            digest.update(chunk)
            out.write(chunk)
        remote_stream(conf, "get {} {}".format(stamp, name), sink, max_bytes)
    return digest.hexdigest()


def parse_sums(text, stamp):
    entries = {}
    for line in text.splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2 or not HEX.fullmatch(parts[0]) or not NAME.fullmatch(parts[1]):
            raise Failure("{}: malformed {} line".format(stamp, SUMS))
        if parts[1] == SUMS or parts[1] in entries:
            raise Failure("{}: bad or duplicate name in {}".format(stamp, SUMS))
        entries[parts[1]] = parts[0]
    for name in REQUIRED:
        if name not in entries:
            raise Failure("{}: {} does not list {}".format(stamp, SUMS, name))
    return entries


def ingest(conf, dest, stamp):
    """Fetch one backup into a fresh .incoming directory, verify it, then publish it read-only."""
    incoming = dest / (".incoming-" + stamp)
    incoming.mkdir(mode=0o700)
    sums_text = remote_text(conf, "get {} {}".format(stamp, SUMS), MAX_SUMS_BYTES)
    entries = parse_sums(sums_text, stamp)
    (incoming / SUMS).write_text(sums_text)
    total = 0
    max_file = conf.getint("max_file_mb") * 1024 * 1024
    for name, expected in sorted(entries.items()):
        check_free_space(conf, dest, max_file)
        actual = fetch_file(conf, stamp, name, incoming / name, max_file)
        if actual != expected:
            raise Failure("{}/{}: checksum mismatch".format(stamp, name))
        total += (incoming / name).stat().st_size
        if total > conf.getint("max_backup_mb") * 1024 * 1024:
            raise Failure("{} is larger than max_backup_mb".format(stamp))
    for entry in incoming.iterdir():
        entry.chmod(0o400)
    incoming.chmod(0o500)
    os.rename(str(incoming), str(dest / stamp))
    return len(entries)


def check_free_space(conf, dest, need_bytes=0):
    free = shutil.disk_usage(str(dest)).free
    if free - need_bytes < conf.getint("min_free_mb") * 1024 * 1024:
        raise Failure("too little free space on {} ({} MB)".format(dest, free // (1024 * 1024)))


def local_backups(dest):
    found = []
    for entry in os.scandir(str(dest)):
        if STAMP.fullmatch(entry.name) and entry.is_dir(follow_symlinks=False):
            found.append(entry.name)
    return sorted(found)


def verify_local(dest, stamp):
    """Re-check a held copy against its own SHA256SUMS; the set of files must match exactly."""
    folder = dest / stamp
    entries = parse_sums((folder / SUMS).read_text(), stamp)
    present = set()
    for entry in os.scandir(str(folder)):
        if not entry.is_file(follow_symlinks=False):
            raise Failure("{}: unexpected non-file {}".format(stamp, entry.name))
        present.add(entry.name)
    if present != set(entries) | {SUMS}:
        raise Failure("{}: files differ from {}".format(stamp, SUMS))
    for name, expected in entries.items():
        digest = hashlib.sha256()
        with open(str(folder / name), "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected:
            raise Failure("{}/{}: checksum mismatch in the local copy".format(stamp, name))


def make_writable(path):
    path.chmod(0o700)
    for entry in path.iterdir():
        if entry.is_file() and not entry.is_symlink():
            entry.chmod(0o600)


def prune(conf, dest, held, now):
    """Keep every copy younger than keep_daily days plus the newest of each of the last
    keep_weekly ISO weeks (the current week counts as one). Never removes the newest."""
    if not held:
        return []
    keep = {held[-1]}
    cutoff = now - datetime.timedelta(days=conf.getint("keep_daily"))
    keep.update(s for s in held if parse_stamp(s) >= cutoff)
    per_week = {}
    for s in held:
        per_week[parse_stamp(s).isocalendar()[:2]] = s
    keep.update(per_week[w] for w in sorted(per_week)[-conf.getint("keep_weekly"):])
    removed = [s for s in held if s not in keep]
    for s in removed:
        make_writable(dest / s)
        shutil.rmtree(str(dest / s))
    return removed


def notify(conf, message):
    url = conf.get("ntfy_url", "") if conf is not None else ""
    if not url:
        log("ALERT NOT SENT (no ntfy_url): " + message)
        return
    try:
        request = urllib.request.Request(url, data=message.encode(), method="POST",
                                         headers={"Title": "Hetzner backup", "Tags": "warning"})
        urllib.request.urlopen(request, timeout=15).close()
    except Exception as error:  # an alert failure must not hide the original failure
        log("ntfy alert failed: {}".format(error))


def write_status(path, status):
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".last-run-")  # O_EXCL: no symlink follow
    with os.fdopen(fd, "w") as handle:
        handle.write(json.dumps(status, indent=2) + "\n")
    os.chmod(tmp, 0o644)
    os.replace(tmp, str(path))


def on_timeout(signum, frame):
    raise Failure("run exceeded {} minutes".format(RUN_TIMEOUT // 60))


def run(conf, dest, status):
    now = utcnow()
    check_free_space(conf, dest)

    for entry in dest.iterdir():  # leftovers of a failed fetch
        if entry.name.startswith(".incoming-") and entry.is_dir() and not entry.is_symlink():
            make_writable(entry)
            shutil.rmtree(str(entry))

    remote = []
    for line in remote_text(conf, "list", 64 * 1024).splitlines():
        if not STAMP.fullmatch(line):
            raise Failure("server listed an invalid name")
        if parse_stamp(line) > now + datetime.timedelta(hours=1):
            raise Failure("server listed a backup dated in the future: {}".format(line))
        remote.append(line)

    held = local_backups(dest)
    for stamp in held:  # a planted future folder must not steer pruning
        if parse_stamp(stamp) > now + datetime.timedelta(hours=1):
            raise Failure("held backup dated in the future: {}".format(stamp))
    # Only backups newer than the newest held one: a held copy is never fetched again, and a
    # backdated name cannot displace an older weekly copy.
    newest_held = held[-1] if held else ""
    new = [s for s in remote if s > newest_held]
    if len(new) > conf.getint("max_new_per_run"):
        raise Failure("server offers {} new backups; at most {} expected".format(
            len(new), conf.getint("max_new_per_run")))
    fetched = []
    for stamp in new:
        files = ingest(conf, dest, stamp)
        fetched.append(stamp)
        log("fetched {} ({} files)".format(stamp, files))

    held = local_backups(dest)
    for stamp in held:
        verify_local(dest, stamp)
    if not held:
        raise Failure("no backups held")
    newest = held[-1]
    age = now - parse_stamp(newest)
    if age > datetime.timedelta(hours=conf.getint("max_age_hours")):
        raise Failure("newest backup {} is {:.0f} hours old".format(newest, age.total_seconds() / 3600))

    removed = prune(conf, dest, held, now)
    limit = conf.getint("keep_daily") + conf.getint("keep_weekly") + 2
    if len(local_backups(dest)) > limit:
        raise Failure("holding more than {} copies after pruning".format(limit))
    remote_text(conf, "done " + newest, 1024)
    status.update(ok=True, newest=newest, fetched=fetched, pruned=removed,
                  held=len(local_backups(dest)), last_success=status["time"])
    log("OK newest={} fetched={} pruned={} held={}".format(newest, len(fetched), len(removed), status["held"]))


def main():
    signal.signal(signal.SIGALRM, on_timeout)
    signal.alarm(RUN_TIMEOUT)
    conf = None
    status_path = None
    status = {"time": utcnow().isoformat(timespec="seconds"), "ok": False}
    try:
        conf = load_config()
        dest = pathlib.Path(conf["dest"])
        status_path = pathlib.Path(conf["status_file"])
        try:
            status["last_success"] = json.loads(status_path.read_text()).get("last_success")
        except (OSError, ValueError):
            pass
        if not dest.is_dir() or dest.is_symlink():
            raise Failure("destination {} is not a directory".format(dest))
        lock_fd = os.open(str(status_path.parent / ".lock"), os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise Failure("another run is active")
        run(conf, dest, status)
        code = 0
    except Exception as error:  # every failure must reach the phone
        message = "{}: {}".format(type(error).__name__, error)
        status["error"] = message
        log("FAILED " + message)
        notify(conf, "OK040 pull failed. " + message)
        code = 1
    finally:
        signal.alarm(0)
    if status_path is not None:
        try:
            write_status(status_path, status)
        except OSError as error:
            log("could not write status: {}".format(error))
            code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
