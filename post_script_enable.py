"""
Add deformers to an object set called "toggle" to enable the deformer with its
"envelope" attribute.
"""
import pymel.core as pc


if pc.objExists("toggle"):
    for member in pc.PyNode("toggle").members():
        member.envelope.set(1)
