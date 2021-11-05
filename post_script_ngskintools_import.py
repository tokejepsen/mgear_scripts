import os

import pymel.core as pc
import ngSkinTools.importExport
import mgear


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
    importer = ngSkinTools.importExport.JsonImporter()
    with open(path) as f:
        data = importer.process(f.read())

        # Setup skinned mesh from influences in file
        joints = [pc.PyNode(x) for x in data.getAllInfluences()]

        # Find mesh from filename
        mesh_name = os.path.splitext(os.path.basename(json_file))[0]
        if not pc.objExists(mesh_name):
            mismatch_files.append(json_file)
            continue
        mesh = pc.PyNode(mesh_name)
        targets.append(mesh)
        skinCluster = pc.skinCluster(
            joints, mesh, skinMethod=2, removeUnusedInfluence=False
        )
        data.saveTo(mesh.name())

if mismatch_files:
    mgear.log(
        "Missing meshes for files:\n{0}".format("\n".join(mismatch_files))
    )

# Reconstruct ngskintools set.
if pc.objExists("ngskintools"):
    pc.delete("ngskintools")

pc.select(clear=True)
object_set = pc.sets(name="ngskintools")

for target in targets:
    object_set.add(pc.PyNode(target))
