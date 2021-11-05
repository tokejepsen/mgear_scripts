"""
Constraints json file schema:
[
    {
        "sources": [
            {
                "node": "spine_C0_2_jnt",
                "weight": 1.0
            }
        ],
        "interp_type": 1,
        "type": "parent",
        "target": "lips_master_null"
    }
]
"""
import os
import json

import pymel.core as pc


basename = os.path.basename(pc.sceneName())
filename = os.path.splitext(basename)[0]
directory = os.path.dirname(pc.sceneName())

# Find "{current file name}/constraints.json"
path = os.path.join(directory, filename, "constraints.json")
targets = []
if os.path.exists(path):
    with open(path, "r") as f:
        for data in json.load(f):
            if not pc.objExists(data["target"]):
                continue

            targets.append(data["target"])
            method = getattr(pc, data["type"] + "Constraint")

            for source in data["sources"]:
                if not pc.objExists(source["node"]):
                    continue

                constraint = method(
                    source["node"],
                    data["target"],
                    weight=source["weight"],
                    maintainOffset=data.get("maintainOffset", True)
                )
                if "interp_type" in data:
                    constraint.interpType.set(data["interp_type"])


# Reconstruct constraints set.
if pc.objExists("constraints"):
    pc.delete("constraints")

pc.select(clear=True)
object_set = pc.sets(name="constraints")

for target in targets:
    object_set.add(pc.PyNode(target))
