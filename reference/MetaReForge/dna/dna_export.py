import bpy
import math
import mathutils
import os
from .libimport import dna, dnacalib, DNA_IMPORT_EX, is_fake
from .io import get_reader, get_writer
from ..utils.blender.object import ensure_objects_visible
from ..utils.blender.keep_state import EditorState

if not is_fake:
    def armature_to_dna(armature_object: bpy.types.Object, calibrated: dnacalib.DNACalibDNAReader):
        
        commands = dnacalib.CommandSequence()
        # armature = bpy.context.scene.objects["Armature"]
        bpy.context.view_layer.objects.active = armature_object
        bpy.ops.object.mode_set(mode='EDIT')

        edit_bones = armature_object.data.edit_bones

        xs, ys, zs = [], [], []
        rot_xs, rot_ys, rot_zs = [], [], []
        
        angle_x = math.radians(-90)  # Replace with your desired rotation angle for X axis
        angle_y = math.radians(0)    # Replace with your desired rotation angle for Y axis
        angle_z = math.radians(0)    # Replace with your desired rotation angle for Z axis

        rotation_x = mathutils.Matrix.Rotation(angle_x, 4, 'X')
        rotation_y = mathutils.Matrix.Rotation(angle_y, 4, 'Y')
        rotation_z = mathutils.Matrix.Rotation(angle_z, 4, 'Z')
        object_rotation = rotation_x @ rotation_y @ rotation_z

        names = {calibrated.getJointName(i): i for i in range(calibrated.getJointCount())}
        for i in range(calibrated.getJointCount()):
            joint_name = calibrated.getJointName(i)
            bone = edit_bones[joint_name]

            # Set the bone head location
            if i == 0:  # No parent, in object space
                # Extracting location, rotation, and scale from the global transformation matrix
                _loc, _rot, _ = (object_rotation @ bone.matrix).decompose()
                # The rotation is represented as a quaternion so convert it to Euler angles
                _rot = _rot.to_euler('XYZ')
            else:         
                # Getting local transformation matrix
                local_matrix = bone.parent.matrix.inverted() @ bone.matrix
                # Extracting location, rotation, and scale from the local transformation matrix
                _loc, _rot, _ = local_matrix.decompose()
                # The rotation is represented as a quaternion so convert it to Euler angles
                _rot = _rot.to_euler('XYZ')
            

            xs.append(_loc[0])
            ys.append(_loc[1])
            zs.append(_loc[2])
            rot_xs.append(math.degrees(_rot[0]))
            rot_ys.append(math.degrees(_rot[1]))
            rot_zs.append(math.degrees(_rot[2]))

            dna_bone_index = names.get(bone.name, None)
            if dna_bone_index is not None:
                original_rot = calibrated.getNeutralJointRotation(dna_bone_index)
                original_rot = [math.radians(angle) for angle in original_rot]
                original_rot = mathutils.Euler(original_rot)
                _rot: mathutils.Euler
        
        set_translations = dnacalib.SetNeutralJointTranslationsCommand(xs, ys, zs)
        set_rotations = dnacalib.SetNeutralJointRotationsCommand(rot_xs, rot_ys, rot_zs)
        commands.add(set_translations)
        commands.add(set_rotations)
        commands.run(calibrated)


    def write_dna(calibrated: dnacalib.DNACalibDNAReader, output_path: str):
        # Write dna
        dna_writer = get_writer(calibrated, output_path)
        dna_writer.write()


    class MRF_OT_write_dna(bpy.types.Operator):
        bl_idname = "meta_reforge.update_dna"
        bl_label = "Update DNA"
        bl_options = {'REGISTER', 'UNDO'}
        
        def execute(self, context):

            print("Updating DNA")
            config = context.scene.meta_reforge_config
            state = EditorState.capture_current_state()
            ensure_objects_visible(config.get_associated_objects())
            
            dna_path = config.absolute_dna_path
            dna_reader = get_reader(dna_path)
            # Copies DNA contents and will serve as input/output parameter to commands
            calibrated = dnacalib.DNACalibDNAReader(dna_reader)
            armature_object = config.fbx_head_armature
            armature_to_dna(armature_object, calibrated)
            filename = os.path.split(dna_path)[1]
            full_path = os.path.join(bpy.path.abspath(config.output_path), filename)
            write_dna(calibrated, full_path)

            print("Update done")
            state.restore_state()
            return {'FINISHED'}
 
    classes = [MRF_OT_write_dna]
else:
    MRF_OT_write_dna = None
    classes = []
    
def register():
    for cls in classes:
        bpy.utils.register_class(cls)   


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
