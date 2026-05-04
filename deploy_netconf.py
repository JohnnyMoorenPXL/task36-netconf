import json
import sys
import requests
from datetime import datetime
from ncclient import manager

LOG_FILE = "deployment.log"


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} - {message}"
    print(line)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_devices(devices_file):
    with open(devices_file, encoding="utf-8") as f:
        return json.load(f)


def get_config(url):
    log(f"Fetching config from {url}")

    response = requests.get(url, timeout=15)
    response.raise_for_status()

    xml_config = response.text.strip()

    if "<native" not in xml_config:
        raise ValueError("Invalid XML: <native> element not found")

    return f"""
<config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
{xml_config}
</config>
"""


def deploy_to_device(device):
    log(f"--- Deploying to {device['name']} ---")

    xml_config = get_config(device["config_url"])
    m = None

    try:
        m = manager.connect(
            host=device["host"],
            port=device["port"],
            username=device["username"],
            password=device["password"],
            hostkey_verify=False,
            device_params={"name": "default"},
            allow_agent=False,
            look_for_keys=False,
            timeout=30
        )

        log(f"{device['name']} - Connected")

        if not any(":candidate" in cap for cap in m.server_capabilities):
            raise RuntimeError("Candidate datastore not supported")

        m.lock(target="candidate")
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

        running = m.get_config(source="running").xml

        if device["name"] in running or "LAB-RA07-A01" in running:
            log(f"{device['name']} - Post-check OK")
        else:
            log(f"{device['name']} - Post-check WARNING: expected hostname not found")

    except Exception as e:
        log(f"{device['name']} - ERROR: {e}")

        if m is not None:
            try:
                m.discard_changes()
                log(f"{device['name']} - discard-changes executed")
            except Exception as discard_error:
                log(f"{device['name']} - discard failed: {discard_error}")

        raise

    finally:
        if m is not None:
            try:
                m.unlock(target="candidate")
                log(f"{device['name']} - Candidate unlocked")
            except Exception as unlock_error:
                log(f"{device['name']} - unlock skipped/failed: {unlock_error}")

            try:
                m.close_session()
                log(f"{device['name']} - NETCONF session closed")
            except Exception:
                pass


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python deploy_netconf.py devices_router.json")
        print("  python deploy_netconf.py devices_switch.json")
        sys.exit(1)

    devices_file = sys.argv[1]
    devices = load_devices(devices_file)

    for device in devices:
        try:
            deploy_to_device(device)
        except Exception as e:
            log(f"{device['name']} - Deployment FAILED: {e}\n")


if __name__ == "__main__":
    main()