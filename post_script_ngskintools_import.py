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
    # Walk through subdirectories to support namespace folders
    for root, dirs, files in os.walk(path):
        for f in files:
            if f.endswith(".json"):
                json_files.append(os.path.join(root, f))

mismatch_files = []
targets = []
for json_file in json_files:
    file_path = json_file
    
    # Calculate mesh name from relative path to support namespaces
    ngskintools_path = os.path.join(directory, filename, "ngskintools")
    relative_path = os.path.relpath(json_file, ngskintools_path)
    
    # Convert path separators back to namespace colons
    if os.path.dirname(relative_path):
        # Has subfolders (namespaces)
        namespace_parts = os.path.dirname(relative_path).split(os.sep)
        filename_part = os.path.splitext(os.path.basename(relative_path))[0]
        mesh_name = ":".join(namespace_parts + [filename_part])
    else:
        # No subfolders (no namespaces)
        mesh_name = os.path.splitext(os.path.basename(relative_path))[0]

    importer = api.transfer.LayersTransfer()
    importer.vertex_transfer_mode = (
        api.transfer.VertexTransferMode.vertexId
    )
    importer.influences_mapping.config = config
    importer.load_source_from_file(file_path, "json")
    importer.target = mesh_name
    joints = []
    for influence_info in importer.influences_mapping.influences:
        joints.append(influence_info.path)
        if not pc.objExists(influence_info.path):
            print("Missing " + influence_info.path)

    # Find mesh from filename
    print(mesh_name)
    if not pc.objExists(mesh_name):
        mismatch_files.append(json_file)
        continue
    mesh = pc.PyNode(mesh_name)
    targets.append(mesh)

    pc.select(clear=True)
    pc.select(sorted(joints), mesh)
    skin_cluster = pc.skinCluster(
        toSelectedBones=True, skinMethod=2, removeUnusedInfluence=False
    )
    skin_cluster.dqsSupportNonRigid.set(True)
    pc.rename(skin_cluster, "{}_skin_cluster".format(mesh_name))
    importer.execute()

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
