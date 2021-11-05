import pymel.core


for node in pymel.core.ls(type="mgear_squashStretch2"):
    node.axis.set(2)