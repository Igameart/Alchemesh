import bpy


def poll_mesh(self, object: bpy.types.Object):
    return True if object.type == 'MESH' else False


def poll_armature(self, object: bpy.types.Object):
    return True if object.type == 'ARMATURE' else False
