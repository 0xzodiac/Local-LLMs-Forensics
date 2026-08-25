#!/usr/bin/env bash
# _detached_run.sh -- reparent-to-init wrapper for long-running harness scripts.
# The harness's run_in_background tracks the immediate process tree; when its
# session cleanup fires, anything still in the tree (parent, children, even
# children detached via os.setsid) gets reaped together because reaping follows
# parent->child links, not session membership.
#
# The fix: launch the actual script via setsid+exec, and have THIS shell exit
# immediately. Result: python is reparented to init/PID 1, the harness sees no
# running job, and the script survives any future session cleanup because it
# has no parent in the harness's tracking.
#
# Usage:
#   bash _detached_run.sh "<full command>" <log-path>
# Example:
#   bash _detached_run.sh "python3 scripts/foo.py --bar" /tmp/foo.log
set -e
CMD="${1:?need a command string}"
LOG="${2:?need a log path}"
# setsid creates a new session; the inner shell does exec to replace itself
# with the actual command. < /dev/null cuts stdin. & puts it in the background
# of THIS shell, then we exit immediately -- leaving the inner process to be
# re-parented to init once the wrapper shell terminates.
setsid bash -c "exec $CMD >> '$LOG' 2>&1" < /dev/null &
WRAPPER_PID=$!
disown
# Print info synchronously so the caller sees what was launched before the
# wrapper exits and the harness can no longer track it.
echo "wrapper_pid=$WRAPPER_PID cmd=$CMD log=$LOG"
