import os
import sys
import json
import importlib

import pymel.core as pm

sys.path.append(os.path.dirname(__file__))

import shrinkwrap_rigger

importlib.reload(shrinkwrap_rigger)


basename = os.path.basename(pm.sceneName())
filename = os.path.splitext(basename)[0]
directory = os.path.dirname(pm.sceneName())

# Find "{current file name}/shrinkwraps.json"
data = []
path = os.path.join(directory, filename, "shrinkwraps")
if os.path.exists(path):
    for f in os.listdir(path):
        if not f.endswith(".shrinkwrap"):
            continue

        with open(os.path.join(path, f)) as f:
            data.append(json.load(f))

object_set = None
if pm.objExists("shrinkwraps"):
    object_set = pm.PyNode("shrinkwraps")
else:
    pm.select(clear=True)
    object_set = pm.sets(name="shrinkwraps")
    pm.addAttr(object_set, longName="data", dataType="string")

object_set.data.set(json.dumps(data))

for rig_data in data:
    shrinkwrap_rigger.rig_from_data(rig_data)
