#!/bin/sh
# Run on the Docker host through the authorised sudo session.
set -eu
PATH=/usr/local/bin:/usr/bin:/bin:$PATH
export PATH
if [ "$#" -lt 4 ] || [ "$#" -gt 6 ]; then
    echo 'Usage: deploy.sh IMAGE_DIGEST NOTES_DIRECTORY ENV_FILE UID:GID [read-only|read-write] [127.0.0.1|100.126.55.95]' >&2
    exit 2
fi
image=$1
notes_directory=$2
environment_file=$3
runtime_user=$4
mount_mode=${5:-read-only}
publish_address=${6:-127.0.0.1}
case "$publish_address" in
    127.0.0.1|100.126.55.95) ;;
    *) echo 'Bind only NAS loopback or the verified Tailscale address.' >&2; exit 2 ;;
esac
case "$mount_mode" in
    read-only) mount_spec="type=bind,source=$notes_directory,target=/notes,readonly" ;;
    read-write) mount_spec="type=bind,source=$notes_directory,target=/notes" ;;
    *) echo 'Choose read-only or read-write mount mode.' >&2; exit 2 ;;
esac
case "$image" in *@sha256:*) ;; *) echo 'An immutable image digest (IMAGE@sha256:...) is required.' >&2; exit 2 ;; esac
image_digest=${image##*@sha256:}
if [ "${#image_digest}" -ne 64 ]; then echo 'Invalid digest length.' >&2; exit 2; fi
case "$image_digest" in *[!a-f0-9]*) echo 'Invalid digest.' >&2; exit 2 ;; esac
case "$runtime_user" in *[!0-9:]*|:*|*:) echo 'Expected numeric UID:GID.' >&2; exit 2 ;; esac
test -f "$notes_directory/README.md"  # an initialised notes store (`volition init`)
test -f "$environment_file"
test ! -L "$notes_directory"
test ! -L "$environment_file"
# A legacy writer must be retired by the layout cutover first.
if docker container inspect keeper >/dev/null 2>&1; then
    echo 'Legacy keeper container exists; use migrate-layout.py before deploying Volition.' >&2
    exit 1
fi
if systemctl is-active --quiet keeper-recover.service 2>/dev/null; then
    echo 'Stop the legacy recovery watcher before deployment.' >&2
    exit 1
fi
docker version >/dev/null
docker pull "$image"
# Preflight with the actual runtime UID and mount before touching an existing service.
docker run --rm --network none --user "$runtime_user" \
    --mount "type=bind,source=$notes_directory,target=/notes,readonly" \
    --entrypoint python "$image" -c 'from pathlib import Path; from volition.store import Store; Store(Path("/notes")).catalogue(limit=1); print("Read preflight passed")'
if docker container inspect volition-previous >/dev/null 2>&1; then
    echo 'A previous container is retained. Review it and explicitly remove it before replacing another version.' >&2
    exit 1
fi
had_previous=0
original_stopped=0
replacement_started=0
rollback() {
    trap - EXIT HUP INT TERM
    echo 'Deployment failed; preserving the failed container and attempting previous-image recovery.' >&2
    if [ "$replacement_started" -eq 1 ] && docker container inspect volition >/dev/null 2>&1; then
        if ! docker stop volition >/dev/null 2>&1; then
            echo 'Cannot stop replacement; previous writer remains stopped. Manual intervention required.' >&2
            exit 1
        fi
        running=$(docker inspect --format '{{.State.Running}}' volition) || exit 1
        if [ "$running" != false ]; then
            echo 'Cannot prove replacement stopped; previous writer remains stopped.' >&2
            exit 1
        fi
        docker rename volition "volition-failed-$(date +%s)"
    fi
    if [ "$had_previous" -eq 1 ]; then
        docker rename volition-previous volition
        docker start volition >/dev/null
    elif [ "$original_stopped" -eq 1 ]; then
        docker start volition >/dev/null
    fi
    exit 1
}
trap rollback EXIT HUP INT TERM
if docker container inspect volition >/dev/null 2>&1; then
    original_stopped=1
    docker stop volition >/dev/null
    docker rename volition volition-previous
    had_previous=1
fi
replacement_started=1
if ! docker run -d --name volition --restart unless-stopped \
    --user "$runtime_user" --read-only --cap-drop ALL --security-opt no-new-privileges \
    --pids-limit 128 --memory 512m --tmpfs /tmp:rw,noexec,nosuid,size=32m \
    --publish "$publish_address:8766:8766" --env-file "$environment_file" \
    --env "VOLITION_PUBLISH_HOST=$publish_address" \
    --mount "$mount_spec" "$image" >/dev/null; then
    rollback
fi
attempt=0
while [ "$attempt" -lt 30 ]; do
    health=$(docker inspect --format '{{.State.Health.Status}}' volition)
    if [ "$health" = healthy ]; then break; fi
    if [ "$health" = unhealthy ]; then rollback; fi
    attempt=$((attempt + 1))
    sleep 2
done
if [ "$health" != healthy ]; then rollback; fi
# Same application/protocol code used by clients; no note bodies in deployment output.
if ! docker exec volition python -m volition.smoke; then rollback; fi
docker inspect --format 'Deployed {{.Config.Image}}; runtime image {{.Image}}; health {{.State.Health.Status}}' volition
trap - EXIT HUP INT TERM
echo 'Previous container retained for rollback. Image rollback does not undo Volition record changes.'
