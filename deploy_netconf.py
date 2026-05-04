from ncclient import manager
import requests

ROUTER = {
    "host": "192.168.1.10",   # <-- jouw router IP
    "port": 830,
    "username": "admin",
    "password": "Cisco123!",
    "hostkey_verify": False
}

GITHUB_URL = "https://raw.githubusercontent.com/JohnnyMoorenPXL/task36-netconf/main/configs/iosxe-full-config.xml"


def get_config():
    print("Config ophalen van GitHub...")
    response = requests.get(GITHUB_URL)
    return response.text


def deploy(xml_config):
    with manager.connect(**ROUTER) as m:
        print("Connected!")

        try:
            m.lock("candidate")

            print("Edit config...")
            m.edit_config(target="candidate", config=xml_config)

            print("Commit...")
            m.commit()

            print("SUCCESS!")

        except Exception as e:
            print("ERROR:", e)
            print("Discard changes...")
            m.discard_changes()

        finally:
            m.unlock("candidate")


if __name__ == "__main__":
    config = get_config()
    deploy(config)