#!/usr/bin/env bash
# Detached supervisor: observe completion without tying apps to the shell process.
# Do not time-limit user actions: an installer or interactive program may be long-lived.
label=${1:-Application}
shift || exit 2
if (( $# == 0 )); then exit 2; fi
"$@"
result=$?
# Ctrl-C / termination is an intentional cancellation, not a failed launch.
if (( result != 0 && result != 130 && result != 143 )); then
  logger -t omarctalia-launcher -- "$label exited with status $result" 2>/dev/null || true
  notify-send -a 'Omarctalia Launcher' -u normal -- \
    'Action did not complete' "$label did not complete successfully. See its output for details." 2>/dev/null || true
fi
exit "$result"
