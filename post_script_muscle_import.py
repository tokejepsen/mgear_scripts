import os
import tempfile
import shutil

from maya import mel
import pymel.core as pm


basename = os.path.basename(pm.sceneName())
filename = os.path.splitext(basename)[0]
directory = os.path.dirname(pm.sceneName())

# Find *.muscle folder starting with same name as current file
maya_files = []
path = os.path.join(directory, filename, "muscles")
if os.path.exists(path):
    for f in os.listdir(path):
        file_path = os.path.join(path, f)
        if f.endswith(".mb") or f.endswith(".ma"):
            maya_files.append(file_path)

# Import all maya files.
for maya_file in maya_files:
    nodes = pm.importFile(maya_file, returnNewNodes=True, namespace="temp")

    namespace = nodes[0].name().split(":")[0]

    # Assumption is that there is only one system and one mesh in each maya
    # file.
    source_system = pm.ls(nodes, type="cMuscleSystem")[0]
    source_mesh = pm.ls(nodes, type="mesh")[0]

    # Setup muscle system
    pm.select(clear=True)
    pm.select(
        pm.PyNode(
            source_mesh.getTransform().name().replace(
                "{}:".format(namespace), ""
            )
        )
    )
    target_system = pm.PyNode(mel.eval("cMuscle_makeMuscleSystem(0)"))
    target_system.smartCollision.set(1)

    # Connect all smart collide data from imported muscle system to created
    # muscle system.
    connections = {}
    attributes = source_system.listConnections(
        type="cMuscleSmartCollide", plugs=True
    )
    for attr in attributes:
        name = attr.listConnections(plugs=True)[0].split(".")[-1]
        connections[name] = attr.node().getTransform()

    for key in sorted(connections.keys()):
        pm.select(clear=True)
        pm.select(connections[key], target_system)
        mel.eval("cMuscleSmartCollide_connectSCToSystem(1)")

    # Transfer muscle system weights.
    directory_name = tempfile.mkdtemp()
    filepath = os.path.join(directory_name, "temp.json").replace("\\", "/")
    weight_types = ["smartregiona", "smartregionb", "smartflatten"]
    for weight_type in weight_types:
        # Remove temp json so no overwrite dialog appears.
        if os.path.exists(filepath):
            os.remove(filepath)

        mel.eval(
            "string $comps[] = cMuscle_getSelComps(\"{0}\", true);"
            "cMSW_save(\"{0}\", \"{1}\", $comps, \"{2}\", 0, 3)".format(
                source_system, filepath, weight_type
            )
        )
        mel.eval(
            "string $comps[] = cMuscle_getSelComps(\"{0}\", true);"
            "cMSW_load(\"{0}\", \"{1}\", $comps, \"{2}\", \"pointorder\", -1"
            ", -1, \"\", \"\", 0, 3, 0);".format(
                target_system, filepath, weight_type
            )
        )
    # Clean up.
    pm.delete(source_mesh.getTransform())
    pm.namespace(removeNamespace=namespace, mergeNamespaceWithRoot=True)
    shutil.rmtree(directory_name)
