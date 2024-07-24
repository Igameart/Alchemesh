import bpy
from ..globals import (
    FBX_HEAD_COLLECTION,
    FBX_BODY_COLLECTION,
    INITIAL_SHAPE_COLLECTION,
    FINAL_SHAPE_COLLECTION
)
from ..utils.blender.collection import collection_set_exclude
from ..utils.blender.object import ensure_objects_visible, ensure_object_visible


def reveal_head_lod(config, lod_index: int) -> None:
    for idx, lod_item in enumerate(config.fbx_head_lods):
        objects = [mesh_item.final_object for mesh_item in lod_item.mesh_items]
        if lod_index == idx:
            ensure_objects_visible(objects)
    for idx, lod_item in enumerate(config.fbx_head_lods):
        if lod_index != idx:
            for mesh_item in lod_item.mesh_items:
                mesh_item.final_object.hide_set(True)


def reveal_body_lod(config, lod_index: int) -> None:
    for idx, lod_item in enumerate(config.fbx_body_lods):
        objects = [mesh_item.final_object for mesh_item in lod_item.mesh_items]
        if lod_index == idx:
            ensure_objects_visible(objects)
    for idx, lod_item in enumerate(config.fbx_body_lods):
        if lod_index != idx:
            for mesh_item in lod_item.mesh_items:
                mesh_item.final_object.hide_set(True)



class MRF_OT_view_picker(bpy.types.Operator):
    bl_idname = "meta_reforge.selector"
    bl_label = "View Picker"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "LOD/Edit Object Picker"

    option: bpy.props.StringProperty(options={"HIDDEN"})
    show_armature: bpy.props.BoolProperty(name="Show Armature", default=True, options={"HIDDEN"})

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return True
     
    def execute(self, context: bpy.types.Context):
        config = context.scene.meta_reforge_config
        collection_set_exclude(FBX_BODY_COLLECTION, True)
        collection_set_exclude(FBX_HEAD_COLLECTION, True)
        collection_set_exclude(INITIAL_SHAPE_COLLECTION, True)
        collection_set_exclude(FINAL_SHAPE_COLLECTION, True)
        if self.option == "FINAL_SHAPE":
            objects = []
            final_armature = config.edit_armature.final_object
            if final_armature:
                objects.append(final_armature)
            for item in config.edit_meshes:
                if item.final_object is not None:
                    objects.append(item.final_object)
            ensure_objects_visible(objects)
            if not self.show_armature and final_armature:
                final_armature.hide_set(True)
                
        elif "LOD" in self.option:
            selector = self.option.split("_")
            if len(selector) == 1:
                self.report({'ERROR'}, f"Invalid LOD index")
                return {'CANCELLED'}
            
            lod_idx_to_reveal = int(selector[1])
            if len(config.fbx_head_lods) == 0 and len(config.fbx_body_lods) == 0:
                self.report({'ERROR'}, f"Invalid LOD index")
                return {'CANCELLED'}
            
            if len(config.fbx_head_lods) == 0:
                reveal_body_lod(config, lod_idx_to_reveal)
            elif len(config.fbx_body_lods) == 0:
                reveal_head_lod(config, lod_idx_to_reveal)
            elif len(config.fbx_head_lods) // len(config.fbx_body_lods) == 2:
                reveal_head_lod(config, lod_idx_to_reveal)
                reveal_body_lod(config, lod_idx_to_reveal // 2)
            else:
                reveal_head_lod(config, lod_idx_to_reveal)
                reveal_body_lod(config, lod_idx_to_reveal)

            if not self.show_armature:
                if config.fbx_head_armature:
                    config.fbx_head_armature.hide_set(True)
                if config.fbx_body_armature:
                    config.fbx_body_armature.hide_set(True)

        return {'FINISHED'}
    

def register():
    bpy.utils.register_class(MRF_OT_view_picker)  


def unregister():
    bpy.utils.unregister_class(MRF_OT_view_picker)  


if __name__ == '__main__':
    register()
