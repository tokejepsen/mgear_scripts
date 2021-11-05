"""
Operates with runtime PointOnPolyConstraint which means it takes the last used
settings. This can make the build wrong, so need to make sure the settings on
PointOnPolyConstraint is reset before building.
PointOnPolyConstraint is also dependent on UVs, so make sure there are no
overlapping UVs.
"""

import operator
from functools import partial
import json

import pymel.core as pm
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from mgear.core import skin, curve, icon, vector
from mgear.vendor.Qt import QtWidgets, QtCore
import mgear.core.pyqt as gqt
from mgear.rigbits import facial_rigger


def create_edge_joint(edge, up_vector_position, up_vector_highest=False):
    # Get the vertices the edge is connected to
    edgeVerts = edge.connectedVertices()

    # Cluster the verts.
    # We will use this to get the position for our joint
    clusTfm = pm.cluster(edgeVerts)[1]

    pm.select(clear=True)
    # Create our joint
    jnt = pm.joint()

    # getPosition doesn't give us the correct result. This does
    pos = clusTfm.rotatePivot.get()
    # We don't need the cluster any more
    pm.delete(clusTfm)

    # Now we calculate the average normal
    normals = []
    for face in edge.connectedFaces():
        # Collect the normal of every face
        normals.append(face.getNormal(space="world"))

    # Variable that will store the sum of all normals
    normalsSum = pm.datatypes.Vector()
    for normal in normals:
        normalsSum += normal

    # This will be our vector for the x axis
    # Average normal.
    # We divide the normal by the total number of vectors
    xVec = (normalsSum / len(normals))

    # The vertex that has the highest position,
    # will be the vertex that our Y axis will point to
    upVec = None
    for i, vert in enumerate(edgeVerts):
        # We take the first vert as our up vector
        if i == 0:
            upVec = edgeVerts[0].getPosition(space="world")

        # And compare the other to it
        vertPos = edgeVerts[i].getPosition(space="world")
        if vertPos[1] >= upVec[1]:
            upVec = vertPos

    # This gives us a vector that points from the center
    # of the selection to the highest vertex
    if up_vector_highest:
        up_vector_position = upVec - pos
    else:
        up_vector_position = up_vector_position - pos

    # We get the z vector from the cross product of our x vector
    # and the up vector
    zVec = xVec.cross(up_vector_position)
    # Calculate the y vec the same way. We could use the up_vector_position
    # but this way we make sure they are all correct
    yVec = zVec.cross(xVec)

    # Normalize all vectors so scaling doesn't get messed up
    xVec.normalize()
    yVec.normalize()
    zVec.normalize()

    # Construct the matrix from the vectors we calculated
    jntMtx = pm.dt.Matrix(-zVec, yVec, xVec, pos)
    # And set the joints matrix to our new matrix
    jnt.setMatrix(jntMtx)

    # This transfers the rotation values
    # to the joint orientation values.
    pm.makeIdentity(jnt, r=True, apply=True)

    return jnt


def order_verts_by_edge_connection(connected_verts, results=[]):
    """
    Orders connected verts by edge connection.
    """
    next_verts = list(
        set(results[-1].connectedVertices()) & set(connected_verts)
    )
    for vert in next_verts:
        if vert not in results:
            results.append(vert)
            break

    return results


def extract_organization_keys(data):
    keys = [
        "setup_group",
        "deformers_group",
        "deformers_set",
        "controls_group",
        "controls_set"
    ]
    results = {}
    for key in keys:
        results[key] = data.get(key)
        if key in data.keys():
            data.pop(key)

    return data, results


def organize_results(data, **kwargs):
    for key, value in kwargs.iteritems():
        if value is None or not value:
            continue

        node = pm.PyNode(value)

        if node.nodeType() == "transform":
            for child in data[key]:
                pm.parent(child, node)

        if node.nodeType() == "objectSet":
            node.addMembers(data[key])


class rename_object(object):

    def __init__(self, node):
        self.node = node
        self.x = node.getTranslation(space="world")[0]
        self.y = node.getTranslation(space="world")[1]
        self.name = ""


def rename_by_position(nodes, tolerance=0.001, prefix="", suffix=""):
    """Rename nodes based on position.

    Finds a unique name by indexing in x axis.
    """
    nodes = [pm.PyNode(x) for x in nodes]

    objects = []
    for node in nodes:
        objects.append(rename_object(node))

    # Sort by y axis, top to bottom
    objects.sort(key=operator.attrgetter("y"))
    objects.reverse()

    # Get positional pairs
    objects_copy = list(objects)
    position_pairs = []
    for count in range(0, len(objects_copy)):
        a = objects_copy[0]
        del(objects_copy[0])
        for b in objects_copy:
            if abs(a.y - b.y) <= tolerance:
                position_pairs.append([a, b])

    # Name positional pairs
    for pair in position_pairs:
        # Sort pairs by x value.
        pair.sort(key=operator.attrgetter("x"))
        index = position_pairs.index(pair) + 1
        pair[0].name = "{0}{1:0>2}".format("Rt", index)
        pair[1].name = "{0}{1:0>2}".format("Lt", index)

    # Name nodes
    center_count = 1
    for object in objects:
        # Non positional pairs will be center "C"
        if not object.name:
            object.name = "{0}{1:0>2}".format("C", center_count)
            center_count += 1

        if prefix:
            object.name = prefix + object.name

        if suffix:
            object.name = object.name + suffix

        pm.rename(object.node, object.name)


def rig(*args, **kwargs):
    tolerance = kwargs["tolerance"]
    kwargs.pop("tolerance")

    kwargs, organization_keys = extract_organization_keys(kwargs)
    results = _rig(*args, **kwargs)
    organize_results(results, **organization_keys)

    # Dont rename master control or pop controls.
    nodes = []
    for node in results["controls_set"]:
        if node.name().endswith("_master_ctrl"):
            continue
        if "pop" in node.name():
            continue
        nodes.append(node)

    prefix = ""
    if "prefix" in kwargs:
        prefix = kwargs["prefix"] + "_"
    rename_by_position(
        nodes, tolerance=tolerance, prefix=prefix, suffix="_ctrl"
    )


def _rig(mesh=None,
         shrinkwrap_mesh=None,
         main_control_start=0,
         main_control_frequency=1,
         up_vector_highest=False,
         flip_direction=False,
         prefix="shrinkwrap_rig",
         control_size=1.0,
         control_offset=0.0,
         mesh_divisions=1):

    results = {"setup_group": [], "controls_group": [], "controls_set": []}

    mesh = pm.duplicate(mesh)[0]
    pm.rename(mesh, prefix + "_wrap")
    results["setup_group"].append(mesh)

    connecting_edges = []
    border_edges = []
    for edge in mesh.edges:
        if edge.isOnBoundary():
            border_edges.append(edge)
        else:
            connecting_edges.append(edge)

    # Split boundary edges into borders
    first_edge_border = [border_edges[0]]
    for count in range(0, len(connecting_edges)):
        for edge in first_edge_border:
            for connected_edge in edge.connectedEdges():
                if not connected_edge.isOnBoundary():
                    continue
                if connected_edge in first_edge_border:
                    continue

                first_edge_border.append(connected_edge)
    second_edge_border = list(
        set(border_edges) - set(first_edge_border)
    )
    border_edges = second_edge_border
    if flip_direction:
        border_edges = first_edge_border
    boundary_verts = []
    for edge in border_edges:
        boundary_verts.extend(edge.connectedVertices())
    boundary_verts = list(set(boundary_verts))

    # Order boundary verts by connection.
    ordered_verts = [boundary_verts[0]]
    for count in range(0, len(boundary_verts)):
        ordered_verts = order_verts_by_edge_connection(
            boundary_verts, ordered_verts
        )

    # Order connecting edges by ordered boundary verts.
    ordered_edges = []
    for vert in ordered_verts:
        for edge in vert.connectedEdges():
            if edge in connecting_edges:
                ordered_edges.append(edge)
    ordered_edges = (
        ordered_edges[main_control_start:] + ordered_edges[:main_control_start]
    )

    # Place joints.
    joints = []
    for edge in ordered_edges:
        up_vector_position = list(
            set(edge.connectedVertices()) & set(ordered_verts)
        )[0].getPosition(space="world")
        joint = create_edge_joint(
            edge, up_vector_position, up_vector_highest
        )
        pm.rename(
            joint,
            "{0}_shrinkwrap{1:0>2}_jnt".format(
                prefix, ordered_edges.index(edge)
            )
        )
        joints.append(joint)

        results["setup_group"].append(joint)

    # Skin mesh. One connected_edge per joint.
    skinCluster = skin.getSkinCluster(mesh)
    if not skinCluster:
        skinCluster = pm.skinCluster(joints, mesh, toSelectedBones=True, nw=2)

    pm.skinPercent(skinCluster, mesh, pruneWeights=100, normalize=False)
    for edge in ordered_edges:
        joint = joints[ordered_edges.index(edge)]
        for vert in edge.connectedVertices():
            pm.skinPercent(skinCluster, vert, transformValue=[(joint, 1.0)])

    # Master control
    clusTfm = pm.cluster(ordered_verts)[1]
    center_position = clusTfm.rotatePivot.get()
    pm.delete(clusTfm)

    master_group = pm.group(name="{0}_master_grp".format(prefix), empty=True)
    master_group.setTranslation(center_position)
    results["controls_group"].append(master_group)

    master_null = pm.duplicate(master_group)[0]
    pm.rename(master_null, "{0}_master_null".format(prefix))
    pm.parent(master_null, master_group)

    points = []
    for joint in joints:
        pm.move(
            joint,
            [0, 0, control_offset],
            relative=True,
            objectSpace=True
        )
        points.append(joint.getTranslation(space="world"))
        pm.move(
            joint,
            [0, 0, -control_offset],
            relative=True,
            objectSpace=True
        )
    master_control = curve.addCurve(
        master_null,
        "{0}_master_ctrl".format(prefix),
        points,
        close=True,
        degree=1
    )
    curve.set_color(master_control, [1, 1, 0])
    pm.makeIdentity(master_control, apply=True)
    master_control.resetFromRestPosition()
    results["controls_set"].append(master_control)

    # Create controls with parent and children. Relationship is determined by
    # skipping edges in the ring. Starting point is configurable.
    # Parent controls
    parent_controls = []
    for joint in joints[::main_control_frequency]:
        group = pm.group(
            name="{0}_main{1:0>2}_grp".format(prefix, joints.index(joint)),
            empty=True
        )
        group.setMatrix(joint.getMatrix())

        null = pm.group(
            name="{0}_main{1:0>2}_null".format(prefix, joints.index(joint)),
            empty=True
        )
        null.setMatrix(joint.getMatrix())

        control = icon.create(
            name="{0}_main{1:0>2}_ctrl".format(prefix, joints.index(joint)),
            icon="cube",
            color=[1, 0, 0]
        )
        control.setMatrix(group.getMatrix())
        pm.rotate(control, [0, 0, 90], relative=True, objectSpace=True)
        results["controls_set"].append(control)

        pm.parent(group, master_control)
        pm.parent(null, group)
        pm.parent(control, null)

        pm.move(
            control,
            [0, 0, control_offset],
            relative=True,
            objectSpace=True
        )
        pm.scale(control, [control_size, control_size, control_size])
        pm.makeIdentity(control, apply=True)
        control.resetFromRestPosition()
        pm.parentConstraint(control, joint)
        parent_controls.append(control)

    # Child controls
    parent_index = 0
    # Duplicate the parent controls to loop back around.
    parents = parent_controls + parent_controls
    for joint in joints:
        if joint in joints[::main_control_frequency]:
            parent_index += 1
            continue

        group = pm.group(
            name="{0}_main{1:0>2}_grp".format(prefix, joints.index(joint)),
            empty=True
        )
        group.setMatrix(joint.getMatrix())

        null = pm.group(
            name="{0}_main{1:0>2}_null".format(prefix, joints.index(joint)),
            empty=True
        )
        null.setMatrix(joint.getMatrix())

        control = icon.create(
            name="{0}_main{1:0>2}_ctrl".format(prefix, joints.index(joint)),
            icon="sphere",
            color=[0, 1, 0]
        )
        control.setMatrix(group.getMatrix())
        pm.rotate(control, [0, 0, 90], relative=True, objectSpace=True)
        results["controls_set"].append(control)

        pm.parent(group, master_control)
        pm.parent(null, group)
        pm.parent(control, null)

        pm.move(
            control,
            [0, 0, control_offset],
            relative=True,
            objectSpace=True
        )
        pm.scale(control, [control_size, control_size, control_size])
        pm.makeIdentity(control, apply=True)
        control.resetFromRestPosition()

        pm.parentConstraint(control, joint)

        weight = parent_index - (
            float(joints.index(joint)) / main_control_frequency
        )
        parent_constraint = pm.parentConstraint(
            parents[parent_index],
            group,
            weight=1.0 - weight,
            maintainOffset=True
        )
        pm.parentConstraint(
            parents[parent_index - 1],
            group,
            weight=weight,
            maintainOffset=True
        )

        parent_constraint.interpType.set(2)

    # Storing vert pairs before subdivding the mesh.
    vert_pairs = []
    for edge in ordered_edges:
        vert_pairs.append(edge.connectedVertices())

    border_verts = pm.ls(
        pm.polyListComponentConversion(
            border_edges, fromEdge=True, toVertex=True
        ),
        flatten=True
    )

    # Adding mesh divisions.
    pm.polySmooth(mesh, divisions=mesh_divisions, keepBorder=False)

    # Setup shrinkwrap
    shrinkWrapNode = pm.deformer(mesh, type="shrinkWrap")[0]
    pm.PyNode(shrinkwrap_mesh).worldMesh[0] >> shrinkWrapNode.targetGeom
    shrinkWrapNode.projection.set(4)

    master_control.addAttr(
        "wobble_smooth",
        min=0,
        max=10
    )
    master_control.wobble_smooth >> shrinkWrapNode.targetSmoothLevel
    master_control.wobble_smooth.set(keyable=False, channelBox=True)

    # Setup point on poly controls.
    # Getting edge loop verts.
    middle_verts = []
    for pair in vert_pairs:
        pm.select(clear=True)
        pm.polySelect(
            mesh,
            shortestEdgePath=(
                pair[0].index(),
                pair[1].index()
            )
        )
        verts = pm.ls(
            pm.polyListComponentConversion(
                pm.ls(selection=True, flatten=True),
                fromEdge=True,
                toVertex=True
            ),
            flatten=True
        )
        edge_count = len(pm.ls(selection=True, flatten=True))
        connected_verts = [pair[0]]
        for count in range(0, edge_count / 2):
            nearest_verts = set(
                pm.ls(connected_verts[-1].connectedVertices(), flatten=True)
            )
            familiar_verts = nearest_verts & set(verts)
            connected_verts.append(
                list(familiar_verts - set(connected_verts))[0]
            )
        middle_verts.append(connected_verts[-1])

    pm.select(clear=True)
    for count in range(0, len(middle_verts)):
        pm.polySelect(
            mesh,
            shortestEdgePath=(
                middle_verts[count - 1].index(), middle_verts[count].index()
            )
        )

    verts = pm.ls(
        pm.polyListComponentConversion(
            pm.ls(selection=True, flatten=True), fromEdge=True, toVertex=True
        ),
        flatten=True
    )

    # Get look at verts.
    edges = []
    for vert in border_verts:
        shortest_distance = None
        targets = list(border_verts)
        targets.remove(vert)
        for target in targets:
            pm.select(clear=True)
            pm.polySelect(
                mesh,
                shortestEdgePath=(
                    vert.index(),
                    target.index()
                )
            )
            selection = pm.ls(selection=True, flatten=True)
            if shortest_distance is None:
                shortest_distance = len(selection)
                vert_edges = selection
            else:
                if len(selection) < shortest_distance:
                    shortest_distance = len(selection)
                    vert_edges = selection
                if len(selection) == shortest_distance:
                    vert_edges.extend(selection)
        edges.extend(vert_edges)

    border_verts = pm.ls(
        pm.polyListComponentConversion(
            edges, fromEdge=True, toVertex=True
        ),
        flatten=True
    )

    look_at_verts = []
    for middle_vert in verts:
        closest_distance = None
        closest_border_vert = None
        for border_vert in border_verts:
            distance = vector.getDistance(
                middle_vert.getPosition(space="world"),
                border_vert.getPosition(space="world")
            )
            if closest_distance is None:
                closest_distance = distance
                closest_border_vert = border_vert
            if distance < closest_distance:
                closest_distance = distance
                closest_border_vert = border_vert

        connected_verts = (
            set(pm.ls(middle_vert.connectedVertices(), flatten=True)) -
            set(middle_verts)
        )
        closest_distance = None
        closest_connected_vert = None
        for connected_vert in connected_verts:
            distance = vector.getDistance(
                closest_border_vert.getPosition(space="world"),
                connected_vert.getPosition(space="world")
            )
            if closest_distance is None:
                closest_distance = distance
                closest_connected_vert = connected_vert
            if distance < closest_distance:
                closest_distance = distance
                closest_connected_vert = connected_vert

        look_at_verts.append(closest_connected_vert)

    # Rig point on poly controls.
    pop_results = _rig_pop(
        verts,
        look_at_verts,
        prefix,
        control_size / 2.0,
        control_offset
    )

    results["setup_group"].extend(pop_results["setup_group"])
    results["controls_group"].extend(pop_results["controls_group"])
    results["controls_set"].extend(pop_results["controls_set"])
    results["deformers_set"] = pop_results["deformers_set"]
    results["deformers_group"] = pop_results["deformers_group"]

    return results


def _rig_pop(verts=[],
             look_at_verts=[],
             prefix="pop_rig",
             control_size=1.0,
             control_offset=0.0):

    results = {
        "setup_group": [],
        "deformers_group": [],
        "deformers_set": [],
        "controls_group": [],
        "controls_set": []
    }

    ordered_verts = [verts[0]]
    for count in range(0, len(verts)):
        ordered_verts = order_verts_by_edge_connection(verts, ordered_verts)

    geo = pm.listRelatives(ordered_verts[0], parent=True)[0]

    for vert in ordered_verts:
        normal_group = pm.group(
            name="{0}_normal{1:0>2}_grp".format(
                prefix, ordered_verts.index(vert)
            ),
            empty=True
        )
        pm.select(vert, normal_group)
        pm.runtime.PointOnPolyConstraint()

        # Break rotation connections
        for attr in ["rx", "ry", "rz"]:
            pm.disconnectAttr("{0}.{1}".format(normal_group, attr))

        pm.normalConstraint(geo, normal_group)

        # Up vector group
        up_vector_group = pm.group(
            name="{0}_up_vector{1:0>2}_grp".format(
                prefix, ordered_verts.index(vert)
            ),
            empty=True
        )
        up_vector_group.setMatrix(normal_group.getMatrix())
        pm.parent(up_vector_group, normal_group)
        up_vector_group.tx.set(0.001)

        # Look at group
        look_at_vert = None
        for connected_vert in vert.connectedVertices():
            if connected_vert in look_at_verts:
                look_at_vert = connected_vert

        look_at_group = pm.group(
            name="{0}_look_at{1:0>2}_grp".format(
                prefix, ordered_verts.index(vert)
            ),
            empty=True
        )
        pm.select(look_at_vert, look_at_group)
        pm.runtime.PointOnPolyConstraint()

        # Parent to setup group
        results["setup_group"].append(normal_group)
        results["setup_group"].append(look_at_group)

        # Transform group
        transform_group = pm.group(
            name="{0}_transform{1:0>2}_grp".format(
                prefix, ordered_verts.index(vert)
            ),
            empty=True
        )
        transform_group.setMatrix(normal_group.getMatrix())
        pm.aimConstraint(
            look_at_group,
            transform_group,
            aimVector=[0, 1, 0],
            upVector=[0, 0, 1],
            worldUpObject=up_vector_group,
            worldUpType="object"
        )
        pm.parent(transform_group, normal_group)

        # Control
        parent_group = pm.group(
            name="{0}_parent{1:0>2}_grp".format(
                prefix, ordered_verts.index(vert)
            ),
            empty=True
        )
        pm.parentConstraint(transform_group, parent_group)
        results["controls_group"].append(parent_group)

        control = icon.create(
            name="{0}_pop{1:0>2}_ctrl".format(
                prefix, ordered_verts.index(vert)
            ),
            icon="sphere",
            color=[0, 0, 1]
        )
        control.setMatrix(parent_group.getMatrix())
        pm.parent(control, parent_group)

        pm.scale(control, [control_size, control_size, control_size])
        pm.move(
            control, [0, 0, (control_offset * (1.0 / control_size)) / 2],
            relative=True,
            objectSpace=True
        )
        pm.makeIdentity(control, apply=True)
        control.resetFromRestPosition()

        results["controls_set"].append(control)

        # Joint
        pm.select(clear=True)
        joint = pm.joint(
            name="{0}_pop{1:0>2}_jnt".format(prefix, ordered_verts.index(vert))
        )
        pm.parentConstraint(control, joint)

        results["deformers_group"].append(joint)
        results["deformers_set"].append(joint)

    return results


class ui(MayaQWidgetDockableMixin, QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(ui, self).__init__(parent)

        self.filter = (
            "Shrinkwrap Rigger Configuration .shrinkwrap (*.shrinkwrap)"
        )

        self.setWindowTitle("Shrinkwrap Rigger")

        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, 1)

        self.main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.main_layout)

        self.create_header_layout()
        self.create_body_layout()
        self.create_footer_layout()

    def create_header_layout(self):

        # prefix
        self.prefix_label = QtWidgets.QLabel("Prefix:")
        self.prefix = QtWidgets.QLineEdit()
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.prefix_label)
        layout.addWidget(self.prefix)
        self.main_layout.addLayout(layout)

        # control_size
        self.control_size_label = QtWidgets.QLabel("Control Size:")
        self.control_size = QtWidgets.QDoubleSpinBox()
        self.control_size.setValue(1)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.control_size_label)
        layout.addWidget(self.control_size)
        self.main_layout.addLayout(layout)

        # control_offset
        self.control_offset_label = QtWidgets.QLabel("Control Offset:")
        self.control_offset = QtWidgets.QDoubleSpinBox()
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.control_offset_label)
        layout.addWidget(self.control_offset)
        self.main_layout.addLayout(layout)

        # tolerance
        self.tolerance_label = QtWidgets.QLabel("Naming tolerance:")
        self.tolerance = QtWidgets.QDoubleSpinBox()
        self.tolerance.setDecimals(3)
        self.tolerance.setValue(0.001)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.tolerance_label)
        layout.addWidget(self.tolerance)
        self.main_layout.addLayout(layout)

    def create_body_layout(self):
        # mesh
        self.mesh_label = QtWidgets.QLabel("Mesh:")
        self.mesh = QtWidgets.QLineEdit()
        self.mesh_button = QtWidgets.QPushButton("<<")
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.mesh_label)
        layout.addWidget(self.mesh)
        layout.addWidget(self.mesh_button)
        self.main_layout.addLayout(layout)

        self.mesh_button.clicked.connect(
            partial(self.populate_object, self.mesh)
        )

        # shrinkwrap_mesh
        self.shrinkwrap_mesh_label = QtWidgets.QLabel("Shrinkwrap Mesh:")
        self.shrinkwrap_mesh = QtWidgets.QLineEdit()
        self.shrinkwrap_mesh_button = QtWidgets.QPushButton("<<")
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.shrinkwrap_mesh_label)
        layout.addWidget(self.shrinkwrap_mesh)
        layout.addWidget(self.shrinkwrap_mesh_button)
        self.main_layout.addLayout(layout)

        self.shrinkwrap_mesh_button.clicked.connect(
            partial(self.populate_object, self.shrinkwrap_mesh)
        )

        # up_vector_highest
        self.up_vector_highest_label = QtWidgets.QLabel("Up Vector Highest:")
        self.up_vector_highest = QtWidgets.QCheckBox()
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.up_vector_highest_label)
        layout.addWidget(self.up_vector_highest)

        # flip_direction
        self.flip_direction_label = QtWidgets.QLabel("Flip Direction:")
        self.flip_direction = QtWidgets.QCheckBox()
        layout.addWidget(self.flip_direction_label)
        layout.addWidget(self.flip_direction)
        self.main_layout.addLayout(layout)

        # main_control_start
        self.main_control_start_label = QtWidgets.QLabel("Main Control Start:")
        self.main_control_start = QtWidgets.QSpinBox()
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.main_control_start_label)
        layout.addWidget(self.main_control_start)
        self.main_layout.addLayout(layout)

        # main_control_frequency
        self.main_control_frequency_label = QtWidgets.QLabel(
            "Main Control Frequency:"
        )
        self.main_control_frequency = QtWidgets.QSpinBox()
        self.main_control_frequency.setMinimum(1)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.main_control_frequency_label)
        layout.addWidget(self.main_control_frequency)
        self.main_layout.addLayout(layout)

        # mesh_divisions
        self.mesh_divisions_label = QtWidgets.QLabel(
            "Mesh Divisions (accuracy):"
        )
        self.mesh_divisions = QtWidgets.QSpinBox()
        self.mesh_divisions.setMinimum(1)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.mesh_divisions_label)
        layout.addWidget(self.mesh_divisions)
        self.main_layout.addLayout(layout)

        # setup_group
        self.setup_group_label = QtWidgets.QLabel("Setup Group:")
        self.setup_group = QtWidgets.QLineEdit()
        self.setup_group_button = QtWidgets.QPushButton("<<")
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.setup_group_label)
        layout.addWidget(self.setup_group)
        layout.addWidget(self.setup_group_button)
        self.main_layout.addLayout(layout)

        self.setup_group_button.clicked.connect(
            partial(self.populate_object, self.setup_group)
        )

        # controls_group
        self.controls_group_label = QtWidgets.QLabel("Controls Group:")
        self.controls_group = QtWidgets.QLineEdit()
        self.controls_group_button = QtWidgets.QPushButton("<<")
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.controls_group_label)
        layout.addWidget(self.controls_group)
        layout.addWidget(self.controls_group_button)
        self.main_layout.addLayout(layout)

        self.controls_group_button.clicked.connect(
            partial(self.populate_object, self.controls_group)
        )

        # controls_set
        self.controls_set_label = QtWidgets.QLabel("Controls Set:")
        self.controls_set = QtWidgets.QLineEdit()
        self.controls_set_button = QtWidgets.QPushButton("<<")
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.controls_set_label)
        layout.addWidget(self.controls_set)
        layout.addWidget(self.controls_set_button)
        self.main_layout.addLayout(layout)

        self.controls_set_button.clicked.connect(
            partial(self.populate_object, self.controls_set)
        )

        # deformers_group
        self.deformers_group_label = QtWidgets.QLabel("Deformers Group:")
        self.deformers_group = QtWidgets.QLineEdit()
        self.deformers_group_button = QtWidgets.QPushButton("<<")
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.deformers_group_label)
        layout.addWidget(self.deformers_group)
        layout.addWidget(self.deformers_group_button)
        self.main_layout.addLayout(layout)

        self.deformers_group_button.clicked.connect(
            partial(self.populate_object, self.deformers_group)
        )

        # deformers_set
        self.deformers_set_label = QtWidgets.QLabel("Deformers Set:")
        self.deformers_set = QtWidgets.QLineEdit()
        self.deformers_set_button = QtWidgets.QPushButton("<<")
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.deformers_set_label)
        layout.addWidget(self.deformers_set)
        layout.addWidget(self.deformers_set_button)
        self.main_layout.addLayout(layout)

        self.deformers_set_button.clicked.connect(
            partial(self.populate_object, self.deformers_set)
        )

    def create_footer_layout(self):
        self.build_button = QtWidgets.QPushButton("Build")
        self.main_layout.addWidget(self.build_button)
        self.build_button.clicked.connect(self.build_rig)

        self.import_button = QtWidgets.QPushButton("Import Config From Json")
        self.main_layout.addWidget(self.import_button)
        self.import_button.clicked.connect(self.import_settings)

        self.export_button = QtWidgets.QPushButton("Export Config To Json")
        self.main_layout.addWidget(self.export_button)
        self.export_button.clicked.connect(self.export_settings)

    def populate_object(self, line_edit):
        selection = pm.selected()
        if selection:
            if len(selection) > 1:
                pm.displayWarning(
                    "Selected more and one object."
                    " Getting first selected object."
                )

            line_edit.setText(selection[0].name())
        else:
            pm.displayWarning("No object selected.")

    def populate_objects(self, line_edit):
        selection = pm.selected(flatten=True)
        if selection:
            line_edit.setText(",".join([node.name() for node in selection]))
        else:
            pm.displayWarning("No objects selected.")

    def build_rig(self):
        kwargs = facial_rigger.lib.get_settings_from_widget(self)
        with pm.UndoChunk():
            rig(**kwargs)

    def export_settings(self):
        data_string = json.dumps(
            facial_rigger.lib.get_settings_from_widget(self),
            indent=4,
            sort_keys=True
        )

        file_path = facial_rigger.lib.get_file_path(self.filter, "save")
        if not file_path:
            return

        with open(file_path, "w") as f:
            f.write(data_string)

    def import_settings(self):
        file_path = facial_rigger.lib.get_file_path(self.filter, "open")
        if not file_path:
            return

        self.import_settings_from_file(file_path)

    def import_settings_from_file(self, file_path):
        facial_rigger.lib.import_settings_from_file(file_path, self)


# Build from json file.
def rig_from_file(path):
    with pm.UndoChunk():
        rig(**json.load(open(path)))


# Build from data.
def rig_from_data(data):
    with pm.UndoChunk():
        rig(**data)


def show(*args):
    return gqt.showDialog(ui)
