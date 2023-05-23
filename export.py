import os
import shutil
import json

import pymel.core as pc
import ngSkinTools.importExport
from studiolibrarymaya import poseitem, animitem
from mgear.shifter import guide_manager


def main():
    basename = os.path.basename(pc.sceneName())
    filename = os.path.splitext(basename)[0]
    directory = os.path.dirname(pc.sceneName())

    if not os.path.exists(os.path.join(directory, filename)):
        os.makedirs(os.path.join(directory, filename))

    # Export connections.
    if pc.objExists("connections"):
        json_data = []
        valid_attributes = [
            "translate",
            "translateX",
            "translateY",
            "translateZ",
            "rotate",
            "rotateX",
            "rotateY",
            "rotateZ",
            "scale",
            "scaleX",
            "scaleY",
            "scaleZ",
            "visibility"
        ]

        for node in pc.PyNode("connections").members():
            connections = node.listConnections(
                source=True, destination=False, plugs=True, connections=True
            )

            # Valid attributes.
            for target, source in connections:
                if source.attrName(longName=True) not in valid_attributes:
                    continue

                exclude_node_types = ["nodeGraphEditorInfo", "objectSet"]
                if source.node().nodeType() in exclude_node_types:
                    continue

                json_data.append(
                    {"source": str(source), "target": str(target)}
                )

            # User defined attributes.
            for target, source in connections:
                if source not in source.node().listAttr(userDefined=True):
                    continue

                json_data.append({
                    "source": str(source),
                    "target": str(target),
                    "keyable": target.get(keyable=True),
                    "channelBox": target.get(channelBox=True)
                })

        path = os.path.join(directory, filename, "connections.json")
        with open(path, "w") as f:
            json.dump(json_data, f, sort_keys=True, indent=4)

    # ngskintools export
    if pc.objExists("ngskintools"):
        path = os.path.join(directory, filename, "ngskintools")
        if not os.path.exists(path):
            os.makedirs(path)

        for mesh in pc.PyNode("ngskintools").members():
            print("Exporting ngskintools on: {}".format(mesh.name()))
            data = ngSkinTools.importExport.LayerData()
            data.loadFrom(mesh.name())
            exporter = ngSkinTools.importExport.JsonExporter()

            filepath = os.path.join(path, "{}.json".format(mesh.name()))
            with open(filepath, "w") as f:
                f.write(exporter.process(data))

    # studiolibrary export
    modes = ["final", "wip"]
    mode = modes[pc.PyNode("guide").mode.get()]
    export_type = "pose"
    exporter = poseitem
    options = {}

    # Export anim when mode is "wip".
    if mode == "wip":
        export_type = "anim"
        exporter = animitem
        options.update(
            {
                "startFrame": pc.playbackOptions(query=True, minTime=True),
                "endFrame": pc.playbackOptions(query=True, maxTime=True),
                "bakeConnected": False
            }
        )

    if pc.objExists("studiolibrary"):
        options = {
            "objects": [x.name() for x in pc.PyNode("studiolibrary").members()]
        }

        path = os.path.join(
            directory,
            filename,
            "studiolibrary",
            "{}.{}".format(mode, export_type)
        )

        if os.path.exists(path):
            shutil.rmtree(path)

        exporter.save(path, **options)

    # Export constraints.
    json_data = []
    constraint_types = [
        "parentConstraint",
        "pointConstraint",
        "orientConstraint",
        "scaleConstraint"
    ]
    if pc.objExists("constraints"):
        for node in pc.PyNode("constraints").members():
            constraints = []
            for constraint_type in constraint_types:
                if node.listRelatives(type=constraint_type):
                    constraints.append(
                        node.listRelatives(type=constraint_type)[0]
                    )

            for constraint in constraints:
                data = {
                    "type": constraint.nodeType().replace("Constraint", ""),
                    "sources": [],
                    "target": node.name()
                }

                # Scale constraints do not have interpType.
                if hasattr(constraint, "interpType"):
                    data["interp_type"] = constraint.interpType.get()

                method = getattr(pc, constraint.nodeType())
                targets = method(constraint, query=True, targetList=True)
                data["constraint_attributes"] = {}
                for target in targets:
                    data["sources"].append(
                        {
                            "node": target.name(),
                            "weight": method(
                                constraint, query=True, weight=target
                            )
                        }
                    )
                    if constraint.nodeType() == "parentConstraint":
                        index = targets.index(target)
                        target_data = {}
                        target = constraint.target[index]
                        target_data["targetOffsetTranslate"] = list(
                            target.targetOffsetTranslate.get()
                        )
                        target_data["targetOffsetRotate"] = list(
                            target.targetOffsetRotate.get()
                        )
                        key = "target[{}]".format(index)
                        data["constraint_attributes"][key] = target_data

                json_data.append(data)

    path = os.path.join(directory, filename, "constraints.json")
    with open(path, "w") as f:
        json.dump(json_data, f, sort_keys=True, indent=4)

    # Extract controls.
    pc.select(pc.PyNode("rig_controllers_grp").members())
    guide_manager.extract_controls()

    # Export display layers.
    display_layers = {}
    for layer in pc.ls(type="displayLayer"):
        # Skip default layer
        if layer.name() == "defaultLayer":
            continue

        display_layers[layer.name()] = {
            "members": [],
            "visibility": layer.visibility.get(),
            "display_type": layer.displayType.get()
        }
        for node in layer.listMembers():
            display_layers[layer.name()]["members"].append(node.name())

    if display_layers:
        path = os.path.join(directory, filename, "display_layers.json")
        with open(path, "w") as f:
            json.dump(display_layers, f, sort_keys=True, indent=4)

    # Extract parents.
    if pc.objExists("parents"):
        data = []
        for node in pc.PyNode("parents").members():
            data.append(
                {"child": node.name(), "parent": node.getParent().name()}
            )

        path = os.path.join(directory, filename, "parents.json")
        with open(path, "w") as f:
            json.dump(data, f, sort_keys=True, indent=4)

    # Extract extra parents.
    if pc.objExists("extra_parents"):
        data = []
        for node in pc.PyNode("extra_parents").members():
            if "controlBuffer" in node.name():
                continue
            data.append(node.name())

        path = os.path.join(directory, filename, "extra_parents.json")
        with open(path, "w") as f:
            json.dump(data, f, sort_keys=True, indent=4)

    # Shrinkwrap rig.
    if pc.objExists("shrinkwraps"):
        folder = os.path.join(directory, filename, "shrinkwraps")

        if not os.path.exists(folder):
            os.makedirs(folder)

        for data in json.loads(pc.PyNode("shrinkwraps").data.get()):
            path = os.path.join(folder, data["prefix"] + ".shrinkwrap")
            with open(path, "w") as f:
                json.dump(data, f, sort_keys=True, indent=4)

    # Eyes rig.
    if pc.objExists("eyes"):
        data = json.loads(pc.PyNode("eyes").data.get())
        for basename in data:
            path = os.path.join(directory, filename, basename)
            with open(path, "w") as f:
                json.dump(data[basename], f, sort_keys=True, indent=4)

    # Export ffds.
    if pc.objExists("ffds"):
        data = {}
        for node in pc.PyNode("ffds").members():
            print(node)
            ffds = node.getShape().listConnections(type="ffd")
            for ffd in ffds:
                try:
                    data[ffd.name()].append(node.name())
                except KeyError:
                    data[ffd.name()] = [node.name()]

        path = os.path.join(directory, filename, "ffds.json")
        with open(path, "w") as f:
            json.dump(data, f, sort_keys=True, indent=4)


if __name__ == "__main__":
    main()
