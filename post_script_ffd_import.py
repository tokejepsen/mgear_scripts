"""
FFDs json file schema:
[
    {
        "ffd8": ["eye_L_over_ctl"]
    }
]
"""
import os
import json

import pymel.core as pc


basename = os.path.basename(pc.sceneName())
filename = os.path.splitext(basename)[0]
directory = os.path.dirname(pc.sceneName())

# Find "{current file name}/ffds.json"
ffds_set = None
if pc.objExists("ffds"):
    ffds_set = pc.PyNode("ffds")
else:
    pc.select(clear=True)
    ffds_set = pc.sets(name="ffds")

path = os.path.join(directory, filename, "ffds.json")
if os.path.exists(path):
    with open(path) as f:
        for key, value in json.load(f).items():
            for node_name in value:
                pc.lattice(key, e=True, remove=False, geometry=node_name)
                ffds_set.add(node_name)
