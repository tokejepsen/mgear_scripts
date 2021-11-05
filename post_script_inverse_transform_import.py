"""
Json schema:
[
    {
        "source": "jaw_C0_ctl",
        "target_driven": "lowerLip_L0_0_jnt",
        "target_driver": "lowerLip_L0_ctl"
    }
]

"""
import os
import json

import pymel.core as pc


basename = os.path.basename(pc.sceneName())
filename = os.path.splitext(basename)[0]
directory = os.path.dirname(pc.sceneName())

path = os.path.join(directory, filename, "inverse_transforms.json")

if os.path.exists(path):
    data = None
    with open(path) as f:
        data = json.load(f)

    with pc.UndoChunk():
        for relationship in data:
            source = pc.PyNode(relationship["source"])
            target_driven = pc.duplicate(
                relationship["target_driven"], parentOnly=True
            )[0]
            pc.rename(
                target_driven, relationship["target_driven"] + "_inverse"
            )
            target_driver = pc.PyNode(relationship["target_driver"])

            link_group = pc.group(
                name="{0}_{1}_link".format(
                    relationship["target_driven"], source
                ),
                empty=True
            )
            link_group.setMatrix(
                target_driven.getParent().getMatrix(worldSpace=True)
            )
            pc.parent(link_group, target_driven.getParent())
            pc.parentConstraint(target_driver, link_group, maintainOffset=True)

            inverse_group = pc.group(
                name="{0}_{1}_inverse".format(
                    relationship["target_driven"], source
                ),
                empty=True
            )
            inverse_group.setMatrix(
                target_driven.getParent().getMatrix(worldSpace=True)
            )
            pc.parent(inverse_group, link_group)

            pc.parent(target_driven, inverse_group)

            decompose_matrix = pc.createNode("decomposeMatrix")

            source.inverseMatrix >> decompose_matrix.inputMatrix
            decompose_matrix.outputTranslate >> inverse_group.translate
            decompose_matrix.outputRotate >> inverse_group.rotate
            decompose_matrix.outputScale >> inverse_group.scale
