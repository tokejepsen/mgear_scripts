import os
import json

import pymel.core as pc
import mgear.rigbits.facial_rigger.eye_rigger


basename = os.path.basename(pc.sceneName())
filename = os.path.splitext(basename)[0]
directory = os.path.dirname(pc.sceneName())

# Find "{current file name}/*.eyes"
path = os.path.join(directory, filename)
eyes_files = []
if os.path.exists(path):
    for f in os.listdir(path):
        if f.endswith(".eyes"):
            eyes_files.append(os.path.join(path, f))

json_data = {}
for eyes_file in eyes_files:
    path = os.path.join(directory, eyes_file)
    with open(path) as data:
        json_data[os.path.basename(path)] = json.load(data)
    mgear.rigbits.facial_rigger.eye_rigger.rig_from_file(path)

object_set = None
if pc.objExists("eyes"):
    object_set = pc.PyNode("eyes")
else:
    pc.select(clear=True)
    object_set = pc.sets(name="eyes")
    pc.addAttr(object_set, longName="data", dataType="string")

object_set.data.set(json.dumps(json_data))
