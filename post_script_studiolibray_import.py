import os

import pymel.core as pc
from studiolibrarymaya import animitem, poseitem


basename = os.path.basename(pc.sceneName())
filename = os.path.splitext(basename)[0]
directory = os.path.dirname(pc.sceneName())

# Find "{current file name}/studiolibrary"
anim_files = {"anim": {}, "pose": {}}
modes = ["final", "wip"]
path = os.path.join(directory, filename, "studiolibrary")
for stage in modes:
    for filetype in anim_files:
        anim_files[filetype][stage] = None

        filepath = os.path.join(path, "{}.{}".format(stage, filetype))
        if os.path.exists(filepath):
            anim_files[filetype][stage] = filepath

# Loading an animation item
mode = pc.PyNode("guide").mode.get()
item = None
objects = []

f = anim_files["anim"][modes[mode]]
if f:
    item = animitem.AnimItem(f)
    objects.extend(item.transferObject().objects().keys())
    item.load(
        option="replace all",
        connect=False,
        currentTime=False
    )

# Loading pose item
f = anim_files["pose"][modes[mode]]
if f:
    item = poseitem.PoseItem(f)
    objects.extend(item.transferObject().objects().keys())
    item.load()

# Reconstruct studiolibrary set.
if item:
    if pc.objExists("studiolibrary"):
        pc.delete("studiolibrary")

    pc.select(clear=True)
    object_set = pc.sets(name="studiolibrary")

    pc.addAttr(object_set, longName="path", dataType="string")
    object_set.path.set(path)

    object_set.add(pc.PyNode("rig"))
    for member in pc.PyNode("rig_controllers_grp").members():
        object_set.add(pc.PyNode(member))

    for object in objects:
        if pc.objExists(object):
            object_set.add(pc.PyNode(object))
