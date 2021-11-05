import os
import json

import pymel.core

import mgear


basename = os.path.basename(pymel.core.sceneName())
filename = os.path.splitext(basename)[0]
directory = os.path.dirname(pymel.core.sceneName())

# Find "{current file name}/display_layers.json"
path = os.path.join(directory, filename, "display_layers.json")
if os.path.exists(path):
    with open(path, "r") as f:
        for layer_name, data in json.load(f).iteritems():
            if not pymel.core.objExists(layer_name):
                pymel.core.createDisplayLayer(name=layer_name, empty=True)

            layer = pymel.core.PyNode(layer_name)

            # Add members
            members = []
            for member in data["members"]:
                if pymel.core.objExists(member):
                    members.append(member)
                else:
                    mgear.log(
                        "Missing {0} for layer: {1}".format(member, layer_name)
                    )
            layer.addMembers(members)

            # Set visibility
            layer.visibility.set(data["visibility"])

            # Set display type.
            layer.displayType.set(data["display_type"])
