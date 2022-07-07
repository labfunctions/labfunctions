import json
import sys

finalpath = "/etc/docker/daemon.json"
# finalpath = "daemon.json"

try:
    mirror = sys.argv[1]

except IndexError:
    print("Any mirror shared")
    sys.exit(0)

if mirror:
    daemon = {"registry-mirrors": [mirror]}

    print("Configuring mirror as ", mirror)
    with open(finalpath, "w") as f:
        f.write(json.dumps(daemon))
else:
    print("No mirror was configurated")
