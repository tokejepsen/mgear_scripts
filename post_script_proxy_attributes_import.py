"""
Proxy attributes json file schema:
[
    {
        "source": "eye_L_over_ctl.blink",
        "target": "eye_L0_ik_ctl.blink"
    }
]
"""
import os
import json

import pymel.core


basename = os.path.basename(pymel.core.sceneName())
filename = os.path.splitext(basename)[0]
directory = os.path.dirname(pymel.core.sceneName())

path = os.path.join(directory, filename, "proxy_attributes.json")
if os.path.exists(path):
    with open(path) as f:
        for data in json.load(f):
            # Add attribute
            if not pymel.core.objExists(data["target"]):
                pymel.core.PyNode(data["target"].split(".")[0]).addAttr(
                    data["target"].split(".")[1],
                    usedAsProxy=True,
                    keyable=True,
                    min=0,
                    max=1
                )

            target_attribute = pymel.core.PyNode(data["target"])

            # Connect attribute
            pymel.core.PyNode(data["source"]).connect(
                target_attribute, force=True
            )
