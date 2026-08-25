import os, signal
for pid in [1695137]:
    try:
        os.kill(pid, signal.SIGKILL)
        print(f"sent SIGKILL to {pid}")
    except ProcessLookupError:
        print(f"{pid} already gone")
