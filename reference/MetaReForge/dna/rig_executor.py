
import math
import bpy
import mathutils
import numpy as np
from .libimport import dna


def find_index(_list, _value):
    try:
        return _list.index(_value)
    except ValueError:
        return None

_rig_logic = None

class Joint:
    def __init__(self, bone: bpy.types.Bone) -> None:
        self.joint_name = bone.name
        self.location = mathutils.Vector()
        self.rotation = mathutils.Vector()
        self.scale = mathutils.Vector([1.0, 1.0, 1.0])
        self.loc_indices = [None, None, None]
        self.rot_indices = [None, None, None]
        self.scale_indices = [None, None, None]
        self.change_location = False
        self.change_rotation = False
        self.change_scale = False
        if bone.parent:
            self.rest2parent_matrix = bone.parent.matrix_local.inverted() @ bone.matrix_local
        else:
            self.rest2parent_matrix = bone.matrix_local
        bone_matrix_parent_space = self.rest2parent_matrix @ mathutils.Matrix.Identity(4)
        # Bone transforms in parent space
        self.rest_location, self.rest_rotation, self.rest_scale = bone_matrix_parent_space.decompose()

    def extract_transforms(self, result) -> None:
        if self.change_location:
            for axis_index, result_index in enumerate(self.loc_indices):
                if result_index != None:
                    self.location[axis_index] = result[result_index]
        if self.change_rotation:
            for axis_index, result_index in enumerate(self.rot_indices):
                if result_index != None:
                    self.rotation[axis_index] = result[result_index]
        if self.change_scale:
            for axis_index, result_index in enumerate(self.scale_indices):
                if result_index != None:
                    self.scale[axis_index] = 1 + result[result_index]
                    
    def apply_transform(self, pose_bone: bpy.types.PoseBone) -> None:
        # Addint transforms in the parent space
        loc = self.rest_location + self.location
        rot = self.rest_rotation.to_euler('XYZ')
        rot.x += self.rotation.x
        rot.y += self.rotation.y
        rot.z += self.rotation.z
        scale = self.rest_scale * self.scale

        # Create scale matrix
        scale_matrix = mathutils.Matrix()
        scale_matrix[0][0], scale_matrix[1][1], scale_matrix[2][2] = scale.x, scale.y, scale.z

        # Compose the matrix from the modified components
        modified_matrix = mathutils.Matrix.LocRotScale(loc, rot, scale)

        # converting back into the space of the rest pose
        pose_bone.matrix_basis = self.rest2parent_matrix.inverted() @ modified_matrix


class JointGroup:
    def __init__(self, armature_object, input_indices, output_indices, values, joints) -> None:
        self.input_indices = np.array(input_indices, dtype=np.int32)
        self.output_indices = output_indices
        self.output_joints = list()
        self.output_axes = list()
        self.output_types = list()
        num_inputs = len(input_indices)
        num_outputs = len(output_indices)
        self.joints = dict()
        for _, joint_name in joints.items():
            bone = armature_object.data.bones.get(joint_name, None)
            if bone is None:
                continue
            self.joints[joint_name] =  Joint(bone)

        self.values = np.zeros(shape=(num_outputs + 1, num_inputs))
        for index, value in enumerate(values):
            loc_output_index = index // num_inputs
            loc_input_index = index % num_inputs
            output_index = output_indices[loc_output_index]
            output_type = output_index % 9 // 3
            self.values[loc_output_index, loc_input_index] = math.radians(value) if output_type == 1 else value

        for index, output_index in enumerate(output_indices):
            joint_index = output_index // 9
            joint_name = joints[joint_index]
            self.output_joints.append(joint_name)
            output_axis = output_index % 3
            output_type = output_index % 9 // 3
            joint = self.joints[joint_name]
            if output_type == 0:
                joint.change_location = True
                joint.loc_indices[output_axis] = index
            elif output_type == 1:
                joint.change_rotation = True
                joint.rot_indices[output_axis] = index
            elif output_type == 2:
                joint.change_scale = True
                joint.scale_indices[output_axis] = index
            self.output_types.append(output_type)
            self.output_axes.append(output_axis)

    def calc(self, controls):
        inputs = controls[self.input_indices]
        result = np.sum(self.values * inputs, axis=1)
        return result


class RigLogicExecutor:
    def __init__(
            self,
            context: bpy.types.Context,
            reader: dna.BinaryStreamReader
        ) -> None:
        self.frame_change_handler = None
        self.pose_change_handler = None
        self._active = False
        self.num_gui_controls = reader.getGUIControlCount()
        self.num_raw_controls = reader.getRawControlCount()
        self.num_psd_controls = reader.getPSDCount()
        self.num_blend_shapes = reader.getBlendShapeChannelCount()
        self.num_joint_groups = reader.getJointGroupCount()
        self.num_joints = reader.getJointCount()
        self.joint_names = list()
        self.joint_groups = dict()
        self.control_values = np.zeros(shape=self.num_raw_controls + self.num_psd_controls)
        self.psd_props = dict()
        self.blend_shapes = dict()

        self.active_pb_name = None
        self.init_raw_controls(context, reader)
        self.init_psd_controls(reader)
        self.init_blend_shape_channels(context, reader)
        self.init_joint_groups(context, reader)

    @property
    def active(self) -> bool:
        return self._active

    
    def run(self) -> None:        
        self.add_frame_change_handler()
        self.add_pose_bone_handler()
        self._active = True

    def resume(self) -> None:
        self._active = True

    def reset(self, scene: bpy.types.Scene) -> None:
        self.reset_blend_shapes(scene)
        self.reset_pose_bones(scene)

    def stop(self) -> None:
        self._active = False

    def init_raw_controls(self, context: bpy.types.Context, reader: dna.BinaryStreamReader) -> None:
        """
        Initialize raw control properties
        """
        # Read raw control names from DNA
        control_names = [reader.getRawControlName(index) for index in range(self.num_raw_controls)]
        # Create Blender CollectionProperty items for each control
        raw_controls = context.scene.meta_reforge_rig_logic.raw_controls
        raw_controls.clear()
        for ctrl_name in control_names:
            item = raw_controls.add()
            item.control_name = ctrl_name

    def init_psd_controls(self, reader: dna.BinaryStreamReader) -> None:
        """
        Initialize PSD control properties
        """
        output_indices = reader.getPSDRowIndices()  # PSD
        input_indices = reader.getPSDColumnIndices()  # RAW indices
        psd_values = reader.getPSDValues()
        psd_props = dict()
        for raw_index, psd_index, weight in zip(input_indices, output_indices, psd_values):
            psd_inputs = psd_props.get(psd_index, None)
            if psd_inputs is None:
                psd_props[psd_index] = psd_inputs = list()
            psd_inputs.append((raw_index, weight))
        
        self.psd_props = psd_props

    def init_blend_shape_channels(self, context: bpy.types.Context, reader: dna.BinaryStreamReader) -> None:
        config = context.scene.meta_reforge_config
        mesh_objects = [item.final_object for item in config.edit_meshes if item.final_object]
        blend_shape_names = [reader.getBlendShapeChannelName(index) for index in range(self.num_blend_shapes)]
        blend_shape_indices = reader.getBlendShapeChannelOutputIndices()
        input_indices = reader.getBlendShapeChannelInputIndices()
        
        self.blend_shapes.clear()
        for mesh_obj in mesh_objects:
            if not mesh_obj.data.shape_keys:
                continue
            bs_map = dict()
            for sk_index, sk in enumerate(mesh_obj.data.shape_keys.key_blocks):
                shape_key_name = sk.name
                parts = shape_key_name.split("__")
                if len(parts) < 2:
                    continue
                sk_channel = "__".join(parts[1:])
                channel_index = find_index(blend_shape_names, sk_channel)
                if channel_index is None:
                    continue

                # Bind to PSD
                array_index = find_index(blend_shape_indices, channel_index)
                if array_index is None:
                    continue

                input_index = input_indices[array_index]  # Input PSD index
                connected_blend_shapes = bs_map.get(input_index, None)
                if connected_blend_shapes is None:
                    bs_map[input_index] = connected_blend_shapes = list()
                connected_blend_shapes.append(sk_index)
            
            self.blend_shapes[mesh_obj.name] = bs_map

    def init_joint_groups(self, context: bpy.types.Context, reader: dna.BinaryStreamReader) -> None:
        armature_obj = context.scene.meta_reforge_config.edit_armature.final_object
        self.joint_names = [reader.getJointName(index) for index in range(self.num_joints)]
        for pb in armature_obj.pose.bones:
            pb.rotation_mode = "XYZ"
        jaw_indices = set()
        for raw_index in range(self.num_raw_controls):
            control_name = reader.getRawControlName(raw_index)
            if "jaw" in control_name.lower():
                jaw_indices.add(raw_index)
        num_joint_groups = reader.getJointGroupCount()

        self.joint_groups.clear()
        for group_index in range(num_joint_groups):
            # The indices of the joints that belong to this group
            # Column (Raw or PSD) indices that the requested joint group contains.
            # The column indices point into the entire, uncompressed joint matrix.
            input_indices = reader.getJointGroupInputIndices(group_index)
            # Row (joint transforms) indices that the requested joint group contains.
            # The row indices point into the entire, uncompressed joint matrix.
            output_indices = reader.getJointGroupOutputIndices(group_index)
            # Values that the requested joint group contains.
            values = reader.getJointGroupValues(group_index)

            joint_indices = reader.getJointGroupJointIndices(group_index)
            joints = {joint_index: self.joint_names[joint_index] for joint_index in joint_indices}
            joint_group = JointGroup(armature_obj, input_indices, output_indices, values, joints)
            self.joint_groups[group_index] = joint_group


    def update_psd(self, psd_index):
        psd_item = self.psd_props.get(psd_index, None)
        result = 1
        for input_index, weight in psd_item:
            result *= self.control_values[input_index] * weight
        self.control_values[psd_index] = round(result, 4)
        return result
    
    def update_psd_controls(self, scene: bpy.types.Scene) -> None:
        raw_controls = scene.meta_reforge_rig_logic.raw_controls
        for index, control in enumerate(raw_controls):
            self.control_values[index] = round(control.value, 4)
        
        for psd_index in self.psd_props:
            self.update_psd(psd_index)

    def update_blend_shapes(self, scene: bpy.types.Scene) -> None:
        config = scene.meta_reforge_config
        mesh_objects = [item.final_object for item in config.edit_meshes if item.final_object]
        for mesh_obj in mesh_objects:
            blend_shapes = self.blend_shapes.get(mesh_obj.name, None)
            if blend_shapes is None:
                continue
            for input_index, bs_indices in blend_shapes.items():
                for bs_index in bs_indices:
                    sk = mesh_obj.data.shape_keys.key_blocks[bs_index]
                    new_value = self.control_values[input_index]
                    if abs(sk.value - new_value) > 1e-5:
                        sk.value = new_value
    
    def reset_blend_shapes(self, scene: bpy.types.Scene) -> None:
        config = scene.meta_reforge_config
        mesh_objects = [item.final_object for item in config.edit_meshes if item.final_object]
        for mesh_obj in mesh_objects:
            blend_shapes = self.blend_shapes.get(mesh_obj.name, None)
            if blend_shapes is None:
                continue
            for bs_indices in blend_shapes.values():
                for bs_index in bs_indices:
                    sk = mesh_obj.data.shape_keys.key_blocks[bs_index]
                    sk.value = 0.0

    def reset_pose_bones(self, scene: bpy.types.Scene) -> None:
        config = scene.meta_reforge_config
        arm = config.edit_armature.final_object
        if arm is not None:
            for pb in arm.pose.bones:
                pb.matrix_basis.identity()


    def update_pose_bones(self, scene: bpy.types.Scene) -> None:
        armature_obj = scene.meta_reforge_config.edit_armature.final_object
        pose_bones = {pb.name: pb for pb in armature_obj.pose.bones}
        for _, joint_group in self.joint_groups.items():
            result = joint_group.calc(self.control_values)
            for joint_name, joint in joint_group.joints.items():
                joint.extract_transforms(result)     
                pb = pose_bones[joint_name]
                joint.apply_transform(pb)

    def full_update(self, scene: bpy.types.Scene) -> None:
        if not self.active:
            return
        self.update_psd_controls(scene)
        self.update_blend_shapes(scene)
        self.update_pose_bones(scene)
    
    def add_frame_change_handler(self):
        self.remove_frame_change_handler()

        def handler(scene):
            self.full_update(scene)

        bpy.app.handlers.frame_change_pre.append(handler)
        self.frame_change_handler = handler

    def remove_frame_change_handler(self):
        if self.frame_change_handler in bpy.app.handlers.frame_change_pre:
            bpy.app.handlers.frame_change_pre.remove(self.frame_change_handler)
        self.frame_change_handler = None


    def add_pose_bone_handler(self):
        self.remove_pose_bone_handler()

        def handler(scene):
            self.full_update(scene)

        bpy.app.handlers.depsgraph_update_pre.append(handler)
        self.pose_change_handler = handler

    def remove_pose_bone_handler(self):
        if self.pose_change_handler in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(self.pose_change_handler)
        self.pose_change_handler = None


def init_executor(context: bpy.types.Context, reader: dna.BinaryStreamReader) -> RigLogicExecutor:
    global _rig_logic
    _rig_logic = RigLogicExecutor(context, reader)
    return _rig_logic


def get_executor() -> RigLogicExecutor:
    global _rig_logic
    if _rig_logic is None:
        return None
    if _rig_logic.pose_change_handler not in bpy.app.handlers.depsgraph_update_pre:
        _rig_logic = None
    return _rig_logic
