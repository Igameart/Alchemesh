import bpy
import traceback
from ..utils.blender.shape_keys import (
    remove_shape_key,
    join_as_shape
)
from ..utils.blender.keep_state import EditorState
from ..utils.blender.object import ensure_objects_visible
from ..utils.transfer_shape_key import transfer_shapekeys, add_delta_noise_shape_key
    

def get_object_by_name(name: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name, None)
    if obj is None:
        raise KeyError(f"Transfer shape object ({name}) is not found")
    
    if obj.type != "MESH":
        raise KeyError(f"Transfer shape object ({name}) is not a mesh")
    return obj


class MRF_OT_transfer_shape(bpy.types.Operator):
    """
    Should be executed from the OBJECT mode
    """
    bl_idname = "meta_reforge.transfer_shape"
    bl_label = "Transfer Shape"
    bl_options = {'REGISTER', 'UNDO'}

    use_noise: bpy.props.BoolProperty(name="Add Noise", default=True, options={"HIDDEN"})
    noise_min_value: bpy.props.FloatProperty(name="Min", default=5e-4, options={"HIDDEN"})
    noise_max_value: bpy.props.FloatProperty(name="Max", default=1e-3, options={"HIDDEN"})
    target_basis: bpy.props.StringProperty(name="Target Object Basis Name", options={"HIDDEN"})
    target: bpy.props.StringProperty(name="Target Object Name", options={"HIDDEN"})
    source_basis: bpy.props.StringProperty(name="Source Basis Object Name", options={"HIDDEN"})
    source_final: bpy.props.StringProperty(name="Source Final Object Name", options={"HIDDEN"})
    laplacian_iterations: bpy.props.IntProperty(name="Laplacian Deform Iterations", options={"HIDDEN"})
    laplacian_threshold: bpy.props.FloatProperty(name="Laplacian Anchor Threshold", options={"HIDDEN"})
    _max_retries = 10

    def execute(self, context):
        try:
            state = EditorState.capture_current_state()
            # Prepare all related objects
            target_obj = get_object_by_name(self.target)
            target_basis_obj = get_object_by_name(self.target_basis)
            source_basis_obj = get_object_by_name(self.source_basis)
            source_final_obj = get_object_by_name(self.source_final)
            ensure_objects_visible([target_obj, target_basis_obj, source_basis_obj, source_final_obj])
            num_retries = 0
            while True:
                try:
                    num_retries += 1
                    final_sk = join_as_shape(source_basis_obj, source_final_obj, "FINAL_SHAPE", replace=True)

                    if self.use_noise:
                        # Delete final delta noise key if it exists
                        remove_shape_key(source_basis_obj, "DELTA_NOISE")
                        # Create a delta noise shape key
                        noise_sk = add_delta_noise_shape_key(
                            obj=source_basis_obj,
                            shape_key_name="DELTA_NOISE",
                            min_limit=self.noise_min_value,
                            max_limit=self.noise_max_value
                        )
                    else:
                        noise_sk = None
                    
                    transfer_shapekeys(
                        context=context,
                        target=target_obj,
                        proxy=target_basis_obj,
                        source=source_basis_obj,
                        basis_shape_key=final_sk.name,
                        bind_key_name=noise_sk.name if noise_sk else None,
                        laplacian_deform=self.laplacian_iterations > 0,
                        laplacian_deform_params={"iterations": self.laplacian_iterations},
                        laplacian_anchor_threshold=self.laplacian_threshold
                    )
                    break
                except Exception as ex:
                    if num_retries < self._max_retries and self.use_noise:
                        print(f"Retry {num_retries}/{self._max_retries}: {str(ex)}")
                    else:
                        raise ex
            
            print("Transfering complete")
            state.restore_state()
            return {'FINISHED'}         
        except Exception as ex:
            self.report({'ERROR'}, f"MRF_OT_transfer_shape operator failed: {str(ex)}")
            print(f"Operator failed: {str(ex)}")
            traceback.print_exc()
            state.try_restore()
            return {'CANCELLED'}
        

class MRF_OT_transfer_shape_target_from_id(bpy.types.Operator):
    """
    Set transfer shape target from edit_id
    """
    bl_idname = "meta_reforge.transfer_shape_target_from_id"
    bl_label = "Transfer Shape"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            config = context.scene.meta_reforge_config
            edit_id = config.emt_edit_id
            for edit_mesh in config.edit_meshes:
                if edit_mesh.edit_id == edit_id:
                    config.emt_source_basis = edit_mesh.basis_object
                    config.emt_source_final = edit_mesh.final_object
                    return {'FINISHED'}
            config.emt_source_basis = None
            config.emt_source_final = None
            return {'FINISHED'}
        except Exception as ex:
            self.report({'ERROR'}, f"MRF_OT_transfer_shape_target_from_id operator failed: {str(ex)}")
            print(f"Operator failed: {str(ex)}")
            traceback.print_exc()
            return {'CANCELLED'}


def register():
    bpy.utils.register_class(MRF_OT_transfer_shape)
    bpy.utils.register_class(MRF_OT_transfer_shape_target_from_id)


def unregister():
    bpy.utils.unregister_class(MRF_OT_transfer_shape)
    bpy.utils.unregister_class(MRF_OT_transfer_shape_target_from_id)
