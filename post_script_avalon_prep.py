import pymel.core as pc


for node in pc.PyNode("controllers_org").listRelatives():
    name = node.name()
    copy = pc.duplicate(node)[0]
    pc.delete(node)
    pc.rename(copy, name)

controls_set = None
if pc.objExists("controls_SET"):
    controls_set = pc.PyNode("controls_SET")
else:
    pc.select(clear=True)
    controls_set = pc.sets(name="controls_SET")

controls_set.addMembers(pc.PyNode("rig_controllers_grp").members())
pc.PyNode("rigMain").addMembers([controls_set])

# Remove control buffer shapes.
for member in controls_set.members():
    if member.name().endswith("controlBuffer"):
        controls_set.remove(member)
