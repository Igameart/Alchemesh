import traceback
import bpy
import mathutils
import typing
import json


def interpolate_bones(
        a_ref: mathutils.Vector,
        b_ref: mathutils.Vector,
        a_target: mathutils.Vector,
        b_target: mathutils.Vector,
        reference_armature: bpy.types.Object,
        target_armature: bpy.types.Object,
        bone_names: typing.List[str]
        ):
    """
    Manipulates the bones of a target armature to match a transformation defined by two segments.

    Args:
        a_ref (mathutils.Vector): Starting coordinate of the reference segment.
        b_ref (mathutils.Vector): Ending coordinate of the reference segment.
        a_target (mathutils.Vector): Starting coordinate of the target segment.
        b_target (mathutils.Vector): Ending coordinate of the target segment.
        reference_armature (bpy.types.Object): The reference armature object.
        target_armature (bpy.types.Object): The target armature object to be manipulated.
        bone_names (list): List of bone names to be manipulated.
    """
    # Set the target armature as the active object and enter edit mode
    bpy.context.view_layer.objects.active = target_armature
    bpy.ops.object.mode_set(mode='EDIT')

    # Calculate direction vectors and transformation components
    ref_vec = b_ref - a_ref
    ref_dir = ref_vec.normalized()
    new_vec = b_target - a_target
    new_dir = new_vec.normalized()

    # Calculate rotation angle and axis
    rot_angle = ref_dir.angle(new_dir)
    rot_axis = ref_dir.cross(new_dir).normalized()
    
    # Calculate scale factor
    scale = new_vec.length / ref_vec.length

    # Create the reference transformation matrix
    ref_matrix = mathutils.Matrix.Translation(a_ref)
    
    # Create the target transformation matrix
    target_location = mathutils.Matrix.Translation(a_target)
    rotation_matrix = mathutils.Matrix.Rotation(rot_angle, 4, rot_axis)
    scale_matrix = mathutils.Matrix.Scale(scale, 4)
    target_matrix = target_location @ rotation_matrix @ scale_matrix

    # Apply transformations to each specified bone
    for bone_name in bone_names:
        ref_bone = reference_armature.data.bones.get(bone_name)
        target_bone = target_armature.data.edit_bones.get(bone_name)
        if ref_bone is None or target_bone is None:
            continue
        
        # Adjusting the bone transformation
        ref_matrix_obj_space = ref_bone.matrix_local.copy()
        ref_matrix_ref_space = ref_matrix.inverted() @ ref_matrix_obj_space
        new_matrix = target_matrix @ ref_matrix_ref_space

        # Decompose to get rotation and location, and combine with original scale
        _, _, scale = target_bone.matrix.decompose()
        loc, rot, _ = new_matrix.decompose()
        target_bone.matrix = mathutils.Matrix.LocRotScale(loc, rot, scale)


class MRF_OT_interpolate_bones(bpy.types.Operator):
    bl_idname = "meta_reforge.interpolate_bones"
    bl_label = "Interpolate Bones"
    bl_description = "Interpolate bones proportions from the reference armature to the target armature"
    bl_options = {'REGISTER', 'UNDO'}

    reference_armature: bpy.props.StringProperty(name="Reference Armature Object Name", default="")
    origin_bone: bpy.props.StringProperty(name="Origin Bone")
    end_bone: bpy.props.StringProperty(name="End Bone")

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.active_object and context.active_object.type == "ARMATURE"
    
    def execute(self, context):
        """
        RUNS FROM ARMATURE EDIT MODE
        """
        try:
            ref_arm = bpy.data.objects.get(self.reference_armature)
            if not ref_arm or ref_arm.type != "ARMATURE":
                self.report({'ERROR'}, "ValueError: Invalid reference object found.")

            bone_names = [bone.name for bone in context.selected_bones]

            a_ref_bone = ref_arm.data.bones.get(self.origin_bone)
            b_ref_bone = ref_arm.data.bones.get(self.end_bone)
            if not a_ref_bone or not b_ref_bone:
                self.report(
                    {'ERROR'},
                    f"Reference armature does not contain {self.origin_bone if not a_ref_bone else self.end_bone}"
                )
            
            target_arm = context.active_object
            a_target_bone = target_arm.data.bones.get(self.origin_bone)
            b_target_bone = target_arm.data.bones.get(self.end_bone)
            if not a_target_bone and not b_target_bone:
                self.report(
                    {'ERROR'},
                    f"Target armature does not contain {self.origin_bone if not a_target_bone else self.end_bone}"
                )
            
            interpolate_bones(
                a_ref=a_ref_bone.head_local,
                b_ref=b_ref_bone.head_local,
                a_target=a_target_bone.head_local,
                b_target=b_target_bone.head_local,
                reference_armature=ref_arm,
                target_armature=target_arm,
                bone_names=bone_names
            )
            return {'FINISHED'}
        except Exception as ex:
            self.report({'ERROR'}, f"MRF_OT_interpolate_bones operation failed: {str(ex)}")
            print(traceback.format_exc())
            return {'CANCELLED'}
        
        
    
classes = [MRF_OT_interpolate_bones]
    

def register():
    for c in classes:
        bpy.utils.register_class(c)   


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)  


if __name__ == '__main__':
    register()
