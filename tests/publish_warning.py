# Standard imports
import datetime as dt
import json

# Third-party imports
import paho.mqtt.publish as publish


fake_message = json.dumps(
    {
        "mac_address": "01:23:45:67:89:A0",
        "node_name": "test node",
        "category": "test category",
        "message": "Ran out of tea",
        "time": dt.datetime.now(tz=dt.timezone.utc).isoformat(
            timespec="milliseconds"
        ),
    }
)


publish.single("/status/warnings", fake_message, hostname="sdr-pnt")
