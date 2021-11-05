"""
Json file schema:
[
    {
        "sources": [
            {"node": "eye_L_over_ctl", "weight": 0.5},
            {"node": "eye_R_over_ctl", "weight": 0.5}
        ],
        "target": "eye_L0_ik_ctl"
    }
]
"""
import os
import json

import pymel.core as pc


basename = os.path.basename(pc.sceneName())
filename = os.path.splitext(basename)[0]
directory = os.path.dirname(pc.sceneName())

# Find *.blendshapes folder starting with same name as current file
json_files = []
for folder in os.listdir(directory):
    folder_name = filename + ".blendshapes"
    if folder == folder_name:
        path = os.path.join(directory, folder_name)
        for f in os.listdir(path):
            if f.endswith(".json"):
                json_files.append(os.path.join(path, f))

for json_file in json_files:
    with open(json_file, "r") as f:
        for data in json.load(f):
            target = data["target"]
            sources = []
            source_weights = []
            for source in data["sources"]:
                sources.append(source["node"])
                source_weights.append(source["weight"])

            blendshape = pc.blendShape(sources, target)
            count = 0
            for weight in source_weights:
                pc.blendShape(blendshape, edit=True, weight=[(count, weight)])
                count += 1
