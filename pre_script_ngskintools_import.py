import os

import pymel.core as pc
from ngSkinTools2 import api
import mgear


config = api.InfluenceMappingConfig()
config.use_distance_matching = True
config.use_name_matching = False

basename = os.path.basename(pc.sceneName())
filename = os.path.splitext(basename)[0]
directory = os.path.dirname(pc.sceneName())

# Find "{current file name}/ngskintools"
json_files = []
path = os.path.join(directory, filename, "ngskintools")
if os.path.exists(path):
    for f in os.listdir(path):
        if f.endswith(".json"):
            json_files.append(os.path.join(path, f))

mismatch_files = []
targets = []
for json_file in json_files:
    path = os.path.join(directory, json_file)
    mesh_name = os.path.splitext(os.path.basename(json_file))[0]

    # Find mesh from filename
    if not pc.objExists(mesh_name):
        mismatch_files.append(json_file)
        continue

    skin_cluster_name = "{}_skin_cluster".format(mesh_name)
    if not pc.objExists(skin_cluster_name):
        continue

    pc.delete(skin_cluster_name)

if mismatch_files:
    mgear.log(
        "Missing meshes for files:\n{0}".format("\n".join(mismatch_files))
    )
