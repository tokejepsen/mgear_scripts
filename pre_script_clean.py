import pymel.core as pm

# Delete all ngSkin nodes
pm.delete(pm.ls(type="ngSkinLayerData"))
# Delete all controller tags
pm.delete(pm.ls(type="controller"))

# Nodes to ensure are deleted.
nodes = ["rig_sets_grp", "rig_controllers_grp", "rig_deformers_grp"]
for node in nodes:
    if not pm.objExists(node):
        continue

    pm.delete(node)
