import pymel.core as pc

import ZvParentMaster


pc.select(clear=True)
pc.select(pc.PyNode("rig_controllers_grp").members())
ZvParentMaster.createParentGroups()
