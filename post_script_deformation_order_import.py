"""
Deformation Order json file schema:
[
    {
        "node": "body_animation",
        "order": [
            "deltaMush1",
            "skinCluster12"
        ]
    }
]
NOTE: Only the inputs that needs changing should be included in the order.
"""
import os
import json

import pymel.core as pc


basename = os.path.basename(pc.sceneName())
filename = os.path.splitext(basename)[0]
directory = os.path.dirname(pc.sceneName())


# Find "{current file name}/deformation_order.json"
path = os.path.join(directory, filename, "deformation_order.json")
targets = []
if os.path.exists(path):
    with open(path, "r") as f:
        for data in json.load(f):
            order = data["order"]
            order.append(data["node"])
            print("Processing {}".format(data["node"]))
            pc.reorderDeformers(order)
