import json
import requests
from datetime import datetime
from ncclient import manager
from ncclient.operations import RPCError

LOG_FILE = "deployment.log"


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} - {message}"
    print(line)

    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def load_devices():
    with open("devices.json") as f:
        return json.load(f)


def get_config(url):
    log(f"Fetching config from {url}")
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    if "<native>" not in response.text:
        raise ValueError("Invalid NETCONF XML config")

    return response.text


def deploy_to_device(device):
    log(f"--- Deploying to {device['name']} ---")

    xml_config = get_config(device["config_url"])

    try:
        with manager.connect(
            host=device["host"],
            port=device["port"],
            username=device["username"],
            password=device["password"],
            hostkey_verify=False,
            device_params={"name": "default"},
            allow_agent=False,
            look_for_keys=False,
            timeout=30
        ) as m:

            log(f"{device['name']} - Connected")

            # Check candidate support
            if not any(":candidate" in cap for cap in m.server_capabilities):
                raise RuntimeError("Candidate datastore not supported")

            m.lock("candidate")
            log(f"{device['name']} - Candidate locked")

            m.discard_changes()
            log(f"{device['name']} - Candidate cleared")

            m.edit_config(
                target="candidate",
                config=xml_config
            )
            log(f"{device['name']} - edit-config OK")

            m.commit()
            log(f"{device['name']} - COMMIT SUCCESS")

            # Post-check
            running = m.get_config(source="running").xml
            if "<hostname>" in running:
                log(f"{device['name']} - Post-check OK")

            m.unlock("candidate")

    except Exception as e:
        log(f"{device['name']} - ERROR: {e}")

        try:
            m.discard_changes()
            log(f"{device['name']} - discard-changes executed")
        except Exception:
            log(f"{device['name']} - discard failed")

        raise


def main():
    devices = load_devices()

    for device in devices:
        try:
            deploy_to_device(device)
        except Exception:
            log(f"{device['name']} - Deployment FAILED\n")


if __name__ == "__main__":
    main()