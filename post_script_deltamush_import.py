import os

import pymel.core


basename = os.path.basename(pymel.core.sceneName())
filename = os.path.splitext(basename)[0]
directory = os.path.dirname(pymel.core.sceneName())

# Find *.deltamush folder starting with same name as current file
json_files = []
for folder in os.listdir(directory):
    if folder == (filename + ".deltamush"):
        path = os.path.join(directory, folder)
        for f in os.listdir(path):
            if f.endswith(".json"):
                json_files.append(os.path.join(path, f))

for json_file in json_files:
    mesh_name = os.path.splitext(os.path.basename(json_file))[0]

    if not pymel.core.objExists(mesh_name):
        raise ValueError(
            "Missing \"{0}\" for delta mush from \"{1}\"".format(
                mesh_name, json_file
            )
        )

    delta_mush = pymel.core.deltaMush(mesh_name)

    pymel.core.deformerWeights(
        os.path.basename(json_file),
        path=os.path.dirname(json_file),
        im=True,
        deformer=delta_mush,
        method="index"
    )
