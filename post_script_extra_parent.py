"""
Parent json file schema:
[
    "arm_L0_fk2_ctl",
    "arm_R0_fk2_ctl"
]
"""
import os
import json

import pymel.core as pc


basename = os.path.basename(pc.sceneName())
filename = os.path.splitext(basename)[0]
directory = os.path.dirname(pc.sceneName())

# Find "{current file name}/extra_parents.json"
extra_parents_set = None
if pc.objExists("extra_parents"):
    extra_parents_set = pc.PyNode("extra_parents")
else:
    pc.select(clear=True)
    extra_parents_set = pc.sets(name="extra_parents")

path = os.path.join(directory, filename, "extra_parents.json")
if os.path.exists(path):
    with open(path) as f:
        for name in json.load(f):
            control = pc.PyNode(name)
            group = pc.group(empty=True)
            group.setMatrix(
                control.getMatrix(worldSpace=True), worldSpace=True
            )
            pc.parent(group, control.getParent())
            pc.parent(control, group)
            pc.rename(group, control.name() + "_extra")

            extra_parents_set.add(control)
