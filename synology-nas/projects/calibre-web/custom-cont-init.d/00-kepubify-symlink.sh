#!/usr/bin/with-contenv bash
# Workaround for https://github.com/janeczku/calibre-web/issues/3679 —
# Calibre-Web's binary detection only recognizes "kepubify-linux-64bit",
# but this image ships the binary as plain "kepubify". A *symlink* doesn't
# work here: resolve_binary_path() calls os.path.realpath() before checking
# the basename, which resolves straight through a symlink back to
# "kepubify" and fails the whitelist check regardless of the symlink's own
# name. So we copy the real file under the expected name instead.
#
# Writes a diagnostics file to /config (host-visible) since this script's
# own stdout only goes to `docker logs`, which isn't reachable from the host.
{
  echo "=== kepubify init check: $(date) ==="
  echo "--- ls -la /usr/bin/kepubify* before ---"
  ls -la /usr/bin/kepubify* 2>&1
  echo "--- whoami / id ---"
  whoami 2>&1; id 2>&1
  if [ -f /usr/bin/kepubify ]; then
    rm -fv /usr/bin/kepubify-linux-64bit 2>&1
    cp -v /usr/bin/kepubify /usr/bin/kepubify-linux-64bit 2>&1
    chmod -v +x /usr/bin/kepubify-linux-64bit 2>&1
    echo "--- ls -la /usr/bin/kepubify* after ---"
    ls -la /usr/bin/kepubify* 2>&1
    echo "--- exec test on the copy ---"
    /usr/bin/kepubify-linux-64bit --version 2>&1
    echo "exit code: $?"
  else
    echo "/usr/bin/kepubify DOES NOT EXIST"
  fi
} > /config/kepubify-init-debug.log 2>&1
