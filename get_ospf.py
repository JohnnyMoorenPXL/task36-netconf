from ncclient import manager

router = {
    "host": "172.16.7.2",
    "port": 830,
    "username": "admin",
    "password": "cisco",
    "hostkey_verify": False,
    "device_params": {"name": "default"},
    "allow_agent": False,
    "look_for_keys": False,
    "timeout": 30
}

filter_xml = """
<native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
  <router>
    <ospf xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-ospf"/>
  </router>
</native>
"""

with manager.connect(**router) as m:
    result = m.get_config(
        source="running",
        filter=("subtree", filter_xml)
    )
    print(result.xml)