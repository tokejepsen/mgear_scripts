import os
import json

import pymel.core as pc


for node in pc.PyNode("controllers_org").listRelatives():
    name = node.name()
    copy = pc.duplicate(node)[0]
    pc.delete(node)
    pc.rename(copy, name)

controls_set = None
if pc.objExists("rigMain_controls_SET"):
    controls_set = pc.PyNode("rigMain_controls_SET")
else:
    pc.select(clear=True)
    controls_set = pc.sets(name="rigMain_controls_SET")


basename = os.path.basename(pc.sceneName())
filename = os.path.splitext(basename)[0]
directory = os.path.dirname(pc.sceneName())

# Find "{current file name}/parents.json"
exclude_set = None
if pc.objExists("exclude_controls"):
    exclude_set = pc.PyNode("exclude_controls")
else:
    pc.select(clear=True)
    exclude_set = pc.sets(name="exclude_controls")

path = os.path.join(directory, filename, "exclude_controls.json")
controls = pc.PyNode("rig_controllers_grp").members()
if os.path.exists(path):
    with open(path) as f:
        for node in json.load(f):
            if node not in controls:
                continue

            controls.remove(node)
            exclude_set.addMembers([node])

controls_set.addMembers(controls)
pc.PyNode("rigMain").addMembers([controls_set])
