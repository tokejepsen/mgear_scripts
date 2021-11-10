"""
Json file schema:
[
    {
        "source": "eye_L_over_ctl.blink",
        "target": "eye_L0_ik_ctl.blink",
        "keyable": true,
        "channelBox": true
    }
]
"""
import os
import json

import pymel.core as pm


basename = os.path.basename(pm.sceneName())
filename = os.path.splitext(basename)[0]
directory = os.path.dirname(pm.sceneName())

# Find "{current file name}/connections.json"
path = os.path.join(directory, filename, "connections.json")
targets = []
if os.path.exists(path):
    with open(path, "r") as f:
        for data in json.load(f):
            # Add source.
            if not pm.objExists(data["source"]):
                pm.PyNode(data["source"].split(".")[0]).addAttr(
                    data["source"].split(".")[1]
                )

            # Add target.
            if not pm.objExists(data["target"]):
                pm.PyNode(data["target"].split(".")[0]).addAttr(
                    data["target"].split(".")[1]
                )

            source = pm.PyNode(data["source"])
            target = pm.PyNode(data["target"])

            source.set(channelBox=data.get("channelBox", True))
            source.set(keyable=data.get("keyable", True))
            target.set(channelBox=data.get("channelBox", False))
            target.set(keyable=data.get("keyable", False))

            source >> target

            targets.append(target.node())

# Reconstruct constraints set.
if pm.objExists("connections"):
    pm.delete("connections")

pm.select(clear=True)
object_set = pm.sets(name="connections")

for target in targets:
    object_set.add(target)