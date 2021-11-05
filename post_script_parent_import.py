"""
Parent json file schema:
[
    {
        "child": "eye_L_over_ctl",
        "parent": "eye_L0_ik_ctl"
    }
]
"""
import os
import json

import pymel.core as pc


basename = os.path.basename(pc.sceneName())
filename = os.path.splitext(basename)[0]
directory = os.path.dirname(pc.sceneName())

# Find "{current file name}/parents.json"
parents_set = None
if pc.objExists("parents"):
    parents_set = pc.PyNode("parents")
else:
    pc.select(clear=True)
    parents_set = pc.sets(name="parents")

path = os.path.join(directory, filename, "parents.json")
if os.path.exists(path):
    with open(path) as f:
        for data in json.load(f):
            child = pc.PyNode(data["child"])
            parent = pc.PyNode(data["parent"])
            pc.parent(child, parent)
            parents_set.add(child)
