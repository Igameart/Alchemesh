import bpy
import json
import mathutils
import os
from ..dna.libimport import dna, dnacalib
from ..dna.io import get_reader
from ..globals import ADDON_DIRECTORY


def create_config(reader: dna.BinaryStreamReader):
    # Create a new armature
    bpy.ops.object.add(type='ARMATURE', enter_editmode=True)
    armature = bpy.context.object
    armature.name = 'Control Rig'
    bpy.context.view_layer.objects.active = armature

    # Switch to edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    
    gui_control_names = [reader.getGUIControlName(index) for index in range(reader.getGUIControlCount())]
    raw_control_names = [reader.getRawControlName(index) for index in range(reader.getRawControlCount())]
    gui_indices = reader.getGUIToRawInputIndices()
    raw_indices = reader.getGUIToRawOutputIndices()
    from_values = reader.getGUIToRawFromValues()
    to_values = reader.getGUIToRawToValues()
    slope_values = reader.getGUIToRawSlopeValues()
    cut_values = reader.getGUIToRawCutValues()
    
    gui_controls = dict()
    raw_controls = dict()
    for gui_index, raw_index, from_value, to_value, slope, cut in zip(
        gui_indices,
        raw_indices,
        from_values,
        to_values,
        slope_values,
        cut_values
    ):
        gui_control_name = gui_control_names[gui_index]
        raw_control_name = raw_control_names[raw_index]
        basename, axis_id = gui_control_name.split(".")
        gui_control = gui_controls.get(basename, None)
        if gui_control is None:
            gui_controls[basename] = gui_control = dict(min_x=0.0, max_x=0.0, min_y=0.0, max_y=0.0)
        
        axis = "Y" if axis_id == "ty" else "X"
        if axis_id == "tx":
            # X-axis
            gui_control["min_x"] = min(from_value, gui_control["min_x"])
            gui_control["max_x"] = max(to_value, gui_control["max_x"])
        elif axis_id == "ty":
            # Y-axis
            gui_control["min_y"] = min(from_value, gui_control["min_y"])
            gui_control["max_y"] = max(to_value, gui_control["max_y"])
        else:
            raise Exception("Unknown axis id")
        
        raw_control = raw_controls.get(raw_control_name, None)
        if raw_control is None:
            raw_controls[raw_control_name] = raw_control = dict(inputs=list())
        raw_control["inputs"].append(
            {
                "input": gui_control_name,
                "from": from_value,
                "to": to_value,
                "cut": cut,
                "slope": slope
            }
        )

    for obj in bpy.context.scene.objects:
        if obj.name.startswith("CTRL_"):
            control_name = obj.name
            _, _, scale = obj.matrix_world.decompose()
            scale_y = abs(scale.y)
            scale_x = abs(scale.x)
            control = gui_controls.get(control_name, None)
            if control is None:
                gui_controls[control_name] = control = dict()
            control.update(
                {
                    "scale_x": scale_x,
                    "scale_y": scale_y,
                    "length": scale_y * 0.1,
                    "matrix": [list(row) for row in obj.matrix_world]
                }
            )

    bpy.data.objects.remove(armature)
    return dict(gui_controls=gui_controls, raw_controls=raw_controls)


class MRF_create_face_controls_config(bpy.types.Operator):
    bl_idname = "meta_reforge.create_face_controls_config"
    bl_label = "Write Rig Logic Congig"


    def execute(self, context):
        # Use get textures
        reader = get_reader("C:/temp/dnacalib/MetaHuman-DNA-Calibration-1.2.0/data/dna_files/Ada.dna")
        config = create_config(reader)

        with open(os.path.join(ADDON_DIRECTORY, "configs", "gui_control", "gui_control.json"), "w") as f:
            json.dump(config, f, indent=4, sort_keys=True)

        return {'FINISHED'}
    


def register():
    bpy.utils.register_class(MRF_create_face_controls_config)

def unregister():
    bpy.utils.unregister_class(MRF_create_face_controls_config)
