import pymel.core as pm

# Delete all ngSkin nodes
pm.delete(pm.ls(type="ngSkinLayerData"))
# Delete all controller tags
pm.delete(pm.ls(type="controller"))
