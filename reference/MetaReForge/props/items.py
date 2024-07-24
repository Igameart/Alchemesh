import bpy
from .poll import poll_armature, poll_mesh


class MRF_object_shape_key_item(bpy.types.PropertyGroup):
    shape_key_name: bpy.props.StringProperty(name="Shape Key Name")
    object: bpy.props.PointerProperty(name="Object", type=bpy.types.Object)


class MRF_shape_key_item(bpy.types.PropertyGroup):
    shape_key_name: bpy.props.StringProperty(name="Text")
    checked: bpy.props.BoolProperty(name="Sync", default=False, description="Enable the shape key synchronization")
    lod_limit: bpy.props.IntProperty(name="LOD limit", default=0, description="LOD limit")


class MRF_mesh_item(bpy.types.PropertyGroup):
    final_object: bpy.props.PointerProperty(name="Final Object", type=bpy.types.Object, poll=poll_mesh)
    basis_object: bpy.props.PointerProperty(name="Basis Object", type=bpy.types.Object, poll=poll_mesh)
    edit_id: bpy.props.StringProperty(name="Edit ID", default="DEFAULT")


class MRF_level_of_detail(bpy.types.PropertyGroup):
    mesh_items: bpy.props.CollectionProperty(name="Mesh Items", type=MRF_mesh_item)
    active_index: bpy.props.IntProperty(name="Active Index")


class MRF_cloth_item(bpy.types.PropertyGroup):
    item_name: bpy.props.StringProperty(name="Item Name", default="Cloth")
    lod_items: bpy.props.CollectionProperty(type=MRF_mesh_item)
    active_lod_index: bpy.props.IntProperty()
    export: bpy.props.BoolProperty(default=True)
    armature: bpy.props.PointerProperty(name="Armature", type=bpy.types.Object, poll=poll_armature)


class MRF_edit_armature(bpy.types.PropertyGroup):
    final_object: bpy.props.PointerProperty(name="Final Armature Object", type=bpy.types.Object, poll=poll_armature)
    basis_object: bpy.props.PointerProperty(name="Basis Armature Object", type=bpy.types.Object, poll=poll_armature)


classes = [
    MRF_shape_key_item,
    MRF_object_shape_key_item,
    MRF_mesh_item,
    MRF_edit_armature,
    MRF_level_of_detail,
    MRF_cloth_item
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
