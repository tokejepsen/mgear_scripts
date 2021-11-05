import pymel.core


muscle_joints = pymel.core.ls(
    pymel.core.PyNode("grpCMuscleSmartCollides"), dagObjects=True, type="joint"
)

for member in pymel.core.PyNode("rig_deformers_grp").members():
    member_name = member.split("|")[-1]
    for muscle_joint in muscle_joints:
        if muscle_joint.split("|")[-1] == member_name:
            pymel.core.parentConstraint(
                member, muscle_joint,maintainOffset=True
            )
