import os
import bpy
import json
import mathutils
from typing import Union

from bpy.types import Context
from ..utils.blender.fbx_io import import_fbx
from ..dna.libimport import dna, dnacalib
from ..dna.io import get_reader
from ..dna.rig_executor import init_executor, get_executor

from ..globals import ADDON_DIRECTORY


def init_rig_logic(context, dna: Union[dna.BinaryStreamReader, dnacalib.DNACalibDNAReader]):
    rig_logic = init_executor(context, dna)
    rig_logic.run()


def add_driver(armature, bone_name, prop_group, prop_name, axis, expression):
    # Getting the bone
    bone = armature.pose.bones.get(bone_name)
    if not bone:
        raise ValueError(f"Bone '{bone_name}' not found in armature")

    # Create a driver
    fcurve = prop_group.driver_add(prop_name)
    driver = fcurve.driver
    driver.type = 'SCRIPTED'
    driver.expression = expression

    # Add variable
    var = driver.variables.get("var")
    if var:
        driver.variables.remove(var)
    var = driver.variables.new()
    var.name = 'var'
    var.type = 'TRANSFORMS'

    # configure the variable target
    target = var.targets[0]
    target.id = armature
    target.transform_type = f"LOC_{axis}" 
    target.transform_space = "LOCAL_SPACE"
    target.bone_target = bone_name

    # Returning the fcurve object for further setup if it is necessary

    return fcurve


def create_control_rig(context: bpy.types.Context, rig_config: dict):
    if context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode='OBJECT')
    
    # Create control rig armature
    armature = bpy.data.objects.get("MRF_CTRL_RIG")
    if armature:
        bpy.data.objects.remove(armature, do_unlink=True)
    bpy.ops.object.add(type='ARMATURE', enter_editmode=True)
    config = context.scene.meta_reforge_rig_logic

    armature = bpy.context.object
    armature.name = "MRF_CTRL_RIG"
    bpy.context.view_layer.objects.active = armature
    config.control_rig = armature

    normal_color = (1.0, 1.0, 0.0)  # Yellow
    active_color = (1.0, 1.0, 1.0)  # White
    select_color = (0.0, 0.0, 1.0)  # Blue
    if hasattr(armature.pose, "bone_groups"):
        # Blender 3.6 and older
        # Create a new bone group
        bone_group = armature.pose.bone_groups.new(name="MetahumanFaceControls")
        bone_group.color_set = "CUSTOM"
        bone_group.colors.normal = normal_color
        bone_group.colors.active = active_color
        bone_group.colors.select = select_color
    else:
        bone_group = None

    gui_controls = rig_config["gui_controls"]
    raw_controls = rig_config["raw_controls"]

    # Switch to edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    for gui_name, gui_data in gui_controls.items():
        bone = armature.data.edit_bones.new(gui_name)
        # Set any nonzero length for the bone before applying the matrix (otherwise the bone will not be rotated)
        if not gui_data.get("length"):
            continue
        bone.length = 1.0
        bone.matrix = mathutils.Matrix(gui_data["matrix"])
        bone.length = gui_data["length"]

    # Switch back to object mode
    bpy.ops.object.mode_set(mode='OBJECT')

    # Import metahuman control rig panel
    frame = bpy.data.objects.get("CONTROLS_FRAME")
    if frame:
        bpy.data.objects.remove(frame, do_unlink=True)
    frame_path = os.path.join(ADDON_DIRECTORY, "third_party", "controls_frame.fbx")
    objects = import_fbx(context=context, fbx_path=frame_path)
    frame = objects[0]
    frame.parent = armature
    frame.hide_select = True

    # Creating a cylinder for bone view
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=1, depth=0.2, enter_editmode=False)
    cylinder = bpy.data.objects.get("MRF_BONE_MESH")
    if cylinder:
        bpy.data.objects.remove(cylinder, do_unlink=True)
    cylinder = bpy.context.object
    cylinder.name = "MRF_BONE_MESH"
    cylinder.hide_set(True)

    # Adding bone constraints
    for gui_name, gui_data in gui_controls.items():
        scale_x, scale_y = gui_data.get("scale_x", None), gui_data.get("scale_y", None) 
        if scale_x is None or scale_y is None:
            continue

        bone = armature.pose.bones[gui_name]
        if bone_group:
            bone.bone_group = bone_group
        else:
            bone.color.palette = 'CUSTOM'
            bone.color.custom.normal = normal_color
            bone.color.custom.active = active_color
            bone.color.custom.select = select_color
            
        bone.lock_rotation = [True, True, True]
        bone.lock_scale = [True, True, True]
        bone.custom_shape = cylinder

        c = bone.constraints.new('LIMIT_LOCATION')
        c.owner_space = "LOCAL"
        c.use_min_x, c.use_max_x = True, True
        c.use_min_y, c.use_max_y = True, True
        c.use_min_z, c.use_max_z = True, True

        if gui_data.get("min_x", None) is None:
            continue

        c.min_x = gui_data["min_x"] * scale_x
        c.max_x = gui_data["max_x"] * scale_x
        c.min_y = gui_data["min_y"] * scale_y
        c.max_y = gui_data["max_y"] * scale_y

    prop = context.scene.meta_reforge_rig_logic
    raw_inputs = {item.control_name: item for item in prop.raw_controls}
    for raw_name, raw_data in raw_controls.items():
        expressions = []
        
        raw_input = raw_inputs.get(raw_name, None)
        if raw_input is None:
            continue
        
        for inp in raw_data["inputs"]:
            basename, axis_id = inp["input"].split(".")
            gui_data = gui_controls.get(basename)
            if gui_data is None:
                # TODO
                continue
            
            if axis_id == "tx":
                scale = gui_data.get("scale_x", None)
            else:
                scale = gui_data.get("scale_y", None)
            if scale is None:
                print("Scale is not found")
                continue
            from_value = inp["from"] * scale
            to_value = inp["to"] * scale
            slope = inp["slope"] / scale
            cut = inp["cut"]
            
            expressions.append((from_value, to_value, slope, cut, scale))
        if basename in armature.pose.bones:
            if len(expressions) == 1:
                from_value, to_value, slope, cut, scale = expressions[0]
                final_expr = f"max(min({to_value}, var), {from_value}) * {slope} + {cut}"
            else:
                parts = []
                for from_value, to_value, slope, cut, scale in expressions:
                    parts.append(f"(var * {slope} + {cut} if {from_value} <= var <= {to_value} else 0.0)")
                final_expr = " + ".join(parts)
            add_driver(armature, basename, raw_input, "value", "X" if axis_id == "tx" else "Y", final_expr)


class MRF_init_rig_logic(bpy.types.Operator):
    bl_idname = "meta_reforge.init_rig_logic"
    bl_label = "Init Rig Logic"


    def execute(self, context):
        # Use get textures
        init_rig_logic(context, get_reader(context.scene.meta_reforge_config.absolute_dna_path))
        with open(os.path.join(ADDON_DIRECTORY, "configs", "gui_control", "gui_control.json"), "r") as f:
            config = json.load(f)
        create_control_rig(context, config)
        return {'FINISHED'}
    
class MRF_run_rig_logic(bpy.types.Operator):
    """
    Starts/Stops handling control updates
    """
    bl_idname = "meta_reforge.switch_rig_logic"
    bl_label = "Switch Rig Logic"

    @classmethod
    def poll(cls, context: Context):
        rig_logic = get_executor()
        return rig_logic


    def execute(self, context):
        rig_logic = get_executor()
        if rig_logic.active:
            rig_logic.stop()
            # rig_logic.reset(context.scene)
        else:
            rig_logic.resume()
            rig_logic.full_update(context.scene)
        return {'FINISHED'}
    

class MRF_reset_edit_objects(bpy.types.Operator):
    """
    Reset the pose of the edit armature and the shape key values of the edit meshes. 
    This is intended to be used when the rig logic is turned off, in order to reset 
    any remaining transformations.
    """
    bl_idname = "meta_reforge.reset_edit_objects"
    bl_label = "Reset Edit Objects"

    @classmethod
    def poll(cls, context: Context):
        rig_logic = get_executor()
        if rig_logic and not rig_logic.active:
            return True
        return False


    def execute(self, context):
        rig_logic = get_executor()
        rig_logic.reset(context.scene)
        return {'FINISHED'}
    

class MRF_toggle_rig_logic_object(bpy.types.Operator):
    bl_idname = "meta_reforge.toggle_rig_logic_object"
    bl_label = "Toggle Rig Logic Pose"

    @classmethod
    def poll(cls, context: Context):
        control_rig = context.scene.meta_reforge_rig_logic.control_rig
        return bool(control_rig)


    def execute(self, context: bpy.types.Context):
        control_rig = context.scene.meta_reforge_rig_logic.control_rig
        # Switch to object mode
        if context.active_object:
            bpy.ops.object.mode_set(mode='OBJECT')

        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')

        control_rig.select_set(True)
        context.view_layer.objects.active = control_rig
        # Enter mesh edit mode
        bpy.ops.object.mode_set(mode='POSE')

        return {'FINISHED'}    


classes = [MRF_init_rig_logic, MRF_run_rig_logic, MRF_toggle_rig_logic_object, MRF_reset_edit_objects]

def register():
    for cl in classes:
        bpy.utils.register_class(cl)

def unregister():
    for cl in classes:
        bpy.utils.unregister_class(cl)
