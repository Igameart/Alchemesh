import bpy
import traceback
from typing import Dict, List
from ..utils.blender.shape_keys import (
    remove_shape_key,
    join_as_shape,
    copy_shape_key
)
from ..utils.blender.keep_state import EditorState
from ..utils.blender.object import ensure_objects_visible
from ..utils.blender.armature import transfer_rest_pose
from ..utils.transfer_shape_key import add_delta_noise_shape_key, transfer_shapekeys


def _sync(self, context: bpy.types.Context, sync_head: bool, sync_body: bool, sync_clothes: bool):
    props = self.properties
    config = context.scene.meta_reforge_config
    print("Synchronization: Preparation...")
    keys = [item.shape_key_name for item in config.sync_shape_keys_to_transfer if item.checked]
    source_objects = dict()
    for item in config.edit_meshes:
        final = item.final_object
        basis = item.basis_object
        final_sk = join_as_shape(basis, final, "FINAL_SHAPE", replace=True)
        for sk_name in keys:
            try:
                copy_shape_key(basis, final, sk_name)
            except (ValueError, AttributeError) as ex:
                pass
        if props.use_noise:
            # Delete final delta noise key if it exists
            remove_shape_key(basis, "DELTA_NOISE")
            # Create a delta noise shape key
            noise_sk = add_delta_noise_shape_key(
                obj=basis,
                shape_key_name="DELTA_NOISE",
                min_limit=props.noise_min_value,
                max_limit=props.noise_max_value
            )
        else:
            noise_sk = None
        source_objects[item.edit_id] = basis

    print("Synchronization: Preparation Complete")

    # Sync head lods
    if sync_head:
        print("Synchronization: Processing Head LODs...")
        for lod_index, lod_item in enumerate(config.fbx_head_lods):
            keys = []
            for item in config.sync_shape_keys_to_transfer:
                if item.checked and item.lod_limit >= lod_index:
                    keys.append(item.shape_key_name)
            for mesh_item in lod_item.mesh_items:
                source_obj = source_objects.get(mesh_item.edit_id, None)
                if source_obj is None:
                    continue
                target_obj = mesh_item.final_object
                basis_object = mesh_item.basis_object
                transfer_shapekeys(
                    context=context,
                    target=target_obj,
                    proxy=basis_object,
                    source=source_obj,
                    basis_shape_key=final_sk.name,
                    bind_key_name=noise_sk.name if noise_sk else None,
                    shape_keys=keys
                )
        print("Synchronization: Processing Head LODs Complete")
    if sync_body:
        print("Synchronization: Processing Body LODs...")
        # Sync body lods
        for lod_index, lod_item in enumerate(config.fbx_body_lods):
            keys = []
            for item in config.sync_shape_keys_to_transfer:
                if item.checked and item.lod_limit >= lod_index:
                    keys.append(item.shape_key_name)
            for mesh_item in lod_item.mesh_items:
                source_obj = source_objects.get(mesh_item.edit_id, None)
                if source_obj is None:
                    continue
                target_obj = mesh_item.final_object
                basis_object = mesh_item.basis_object
                transfer_shapekeys(
                    context=context,
                    target=target_obj,
                    proxy=basis_object,
                    source=source_obj,
                    basis_shape_key=final_sk.name,
                    bind_key_name=noise_sk.name if noise_sk else None,
                    shape_keys=keys
                )
        print("Synchronization: Processing Body LODs Complete")

    if sync_clothes:
        # Sync clothes
        print("Synchronization: Processing cloth...")
        for cloth_item in config.cloth_items:
            for mesh_item in cloth_item.lod_items:
                source_obj = source_objects.get(mesh_item.edit_id, None)
                if source_obj is None:
                    continue
                target_obj = mesh_item.final_object
                basis_object = mesh_item.basis_object
                transfer_shapekeys(
                    context=context,
                    target=target_obj,
                    proxy=basis_object,
                    source=source_obj,
                    basis_shape_key=final_sk.name,
                    bind_key_name=noise_sk.name if noise_sk else None,
                    shape_keys=keys
                )
        print("Synchronization: Processing cloth Complete")

    armatures_to_sync = []
    # Syncronize armatures
    if sync_head and config.fbx_head_armature:
        armatures_to_sync.append(config.fbx_head_armature)
    if sync_body and config.fbx_body_armature:
        armatures_to_sync.append(config.fbx_body_armature)
    if sync_clothes:
        for item in config.cloth_items:
            if item.armature is None:
                print(f"Invalid armature for cloth {item.item_name}")
                continue
            armatures_to_sync.append(item.armature)
    
    print("Synchronization: Processing armatures")
    for arm in armatures_to_sync:
        transfer_rest_pose(config.edit_armature.final_object, arm)
    print("Synchronization: Processing armatures Complete")


class MRF_OT_synchronize(bpy.types.Operator):
    """
    Synchronize the edit object with head/body/clothes LODs that will be exported to UE as FBX
    Should be executed from the OBJECT mode
    """
    bl_idname = "meta_reforge.sync"
    bl_label = "Sync Meshes"
    bl_options = {'REGISTER', 'UNDO'}

    use_noise: bpy.props.BoolProperty(name="Add Noise", default=True, options={"HIDDEN"})
    noise_min_value: bpy.props.FloatProperty(name="Min", default=5e-4, options={"HIDDEN"})
    noise_max_value: bpy.props.FloatProperty(name="Max", default=1e-3, options={"HIDDEN"})
    sync_head: bpy.props.BoolProperty(name="Sync Head", default=True, options={"HIDDEN"})
    sync_body: bpy.props.BoolProperty(name="Sync Body", default=True, options={"HIDDEN"})
    sync_clothes: bpy.props.BoolProperty(name="Sync Clothes", default=True, options={"HIDDEN"})

    _max_retries = 10

    def execute(self, context):
        try:
            config = context.scene.meta_reforge_config
            state = EditorState.capture_current_state()
            ensure_objects_visible(config.get_associated_objects())
            num_retries = 0
            while True:
                try:
                    num_retries += 1
                    _sync(self, context, self.sync_head, self.sync_body, self.sync_clothes)
                    break
                except Exception as ex:
                    if self.use_noise and num_retries < self._max_retries:
                        print(f"Retry {num_retries}/{self._max_retries}: {str(ex)}")
                    else:
                        raise ex
            
            print("Synchronization complete")
            state.restore_state()
            return {'FINISHED'}         
        except Exception as ex:
            self.report({'ERROR'}, f"MRF_OT_synchronize operation failed: {str(ex)}")
            print(f"Operation failed: {str(ex)}")
            traceback.print_exc()
            state.try_restore()
            return {'CANCELLED'}
        

class MRF_OT_update_shape_keys_to_sync(bpy.types.Operator):
    """
    Updates the list of shape keys (morph targets) to syncronize
    """
    bl_idname = "meta_reforge.update_shape_keys_to_sync"
    bl_label = "Update Shape Keys"
    bl_options = {'REGISTER', 'UNDO'}

    reset_value: bpy.props.BoolProperty(name="Default Value", default=False, options={"HIDDEN"})
    reset: bpy.props.BoolProperty(name="Reset", default=False, options={"HIDDEN"})

    def execute(self, context):
        try:
            config = context.scene.meta_reforge_config
            old_values = {
                item.shape_key_name: (item.checked, item.lod_limit) for item in config.sync_shape_keys_to_transfer
            }
            config.sync_shape_keys_to_transfer.clear()
            shape_keys = set()
            for item in config.edit_meshes:
                obj = item.final_object
                if obj is None or obj.data.shape_keys is None:
                    continue
                obj_keys = [sk.name for sk in obj.data.shape_keys.key_blocks]
                shape_keys.update(obj_keys[1:])
            
            shape_keys = sorted(list(shape_keys))
            for shape_key in shape_keys:
                item = config.sync_shape_keys_to_transfer.add()
                item.shape_key_name = shape_key
                checked, lod_limit = old_values.get(shape_key, (False, 0))
                if self.reset:
                    item.checked = self.reset_value
                    item.lod_limit = lod_limit
                else:
                    item.checked = checked
                    item.lod_limit = lod_limit
            return {'FINISHED'}         
        except Exception as ex:
            self.report({'ERROR'}, f"MRF_OT_synchronize operation failed: {str(ex)}")
            print(f"Operation failed: {str(ex)}")
            traceback.print_exc()
            return {'CANCELLED'}


def register():
    bpy.utils.register_class(MRF_OT_synchronize)
    bpy.utils.register_class(MRF_OT_update_shape_keys_to_sync)  


def unregister():
    bpy.utils.unregister_class(MRF_OT_synchronize)
    bpy.utils.unregister_class(MRF_OT_update_shape_keys_to_sync)  
