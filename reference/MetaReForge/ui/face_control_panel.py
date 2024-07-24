import bpy
from ..operators.control_rig import (
    MRF_init_rig_logic,
    MRF_run_rig_logic,
    MRF_toggle_rig_logic_object,
    MRF_reset_edit_objects
)
from ..dna.rig_executor import get_executor
from ..operators.control_rig_config import MRF_create_face_controls_config
from ..operators.update_shape_keys import (
    MRF_OT_scan_nonzero_shape_keys,
    MRF_OT_edit_shape_key,
    MRF_OT_check_shape_key
)
from ..dna.libimport import is_fake


class MRF_UL_shape_key_item(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        main_row = layout.row()
        col = main_row.column()
        col.label(text=item.shape_key_name)
        col = main_row.column()

        sk_value = item.object.data.shape_keys.key_blocks[item.shape_key_name].value
        row = col.row()
        row.label(text=f"{sk_value:.2f}")
        
        row = row.row(align=True)
        op_props = row.operator(MRF_OT_check_shape_key.bl_idname, text="", icon="CHECKMARK")
        op_props.shape_key_name = item.shape_key_name

        op_props = row.operator(MRF_OT_edit_shape_key.bl_idname, text="", icon="SCULPTMODE_HLT")
        op_props.shape_key_name = item.shape_key_name
        op_props.object_name = item.object.name
        op_props.mode = "SCULPT"

        op_props = row.operator(MRF_OT_edit_shape_key.bl_idname, text="", icon="EDITMODE_HLT")
        op_props.shape_key_name = item.shape_key_name
        op_props.object_name = item.object.name
        op_props.mode = "EDIT"
    
    def filter_items(self, context, data, propname):
        # Obtain the actual list of items
        items = getattr(data, propname)

        # Filter flags: 0 means item is filtered, 1 means item is not filtered
        filter_flags = []
        # Reordering indices: keeps track of the original order
        order = []

        # Check each item
        for idx, item in enumerate(items):
            if self.filter_name.lower() in item.shape_key_name.lower():
                filter_flags.append(self.bitflag_filter_item)
            else:
                filter_flags.append(0)
            order.append(idx)

        # The method must return a tuple of two lists
        return (filter_flags, order)


class MRF_UL_control_item(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        active_index = getattr(active_data, active_propname)
        if active_index == index:
            row.label(text="", icon="RADIOBUT_ON")
        else:
            row.label(text="", icon="RADIOBUT_OFF")
        row.prop(item, "value", text=item.control_name, slider=True)

    def filter_items(self, context, data, propname):
        # Obtain the actual list of items
        items = getattr(data, propname)

        # Filter flags: 0 means item is filtered, 1 means item is not filtered
        filter_flags = []
        # Reordering indices: keeps track of the original order
        order = []

        # Check each item
        for idx, item in enumerate(items):
            if self.filter_name.lower() in item.control_name.lower():
                filter_flags.append(self.bitflag_filter_item)
            else:
                filter_flags.append(0)
            order.append(idx)

        # The method must return a tuple of two lists
        return (filter_flags, order)


class MRF_PT_face_control_panel(bpy.types.Panel):
    """
    Addon main menu (N-Panel)
    """
    bl_label = "MetaReForge.FaceControls"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MRF"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        # layout.operator(MRF_create_face_controls_config.bl_idname)
        layout.operator(MRF_init_rig_logic.bl_idname)
        rig_logic = get_executor()
        if rig_logic:
            if rig_logic.active:
                layout.operator(MRF_run_rig_logic.bl_idname, text="Turn OFF Rig Logic", icon="RADIOBUT_ON")
            else:
                layout.operator(MRF_run_rig_logic.bl_idname, text="Turn ON Rig Logic", icon="RADIOBUT_OFF")
            layout.operator(MRF_reset_edit_objects.bl_idname, text="Reset Edit Objects", icon="CANCEL")
        
        layout.operator(MRF_toggle_rig_logic_object.bl_idname, text="Edit Pose", icon="POSE_HLT")
        rig_logic = context.scene.meta_reforge_rig_logic

        box = layout.box()
        box.label(text="Corrective Shape Keys")
        config = context.scene.meta_reforge_config
        
        box.template_list(
            listtype_name="MRF_UL_shape_key_item", list_id="",
            dataptr=config, propname="nonzero_shape_keys",
            active_dataptr=config, active_propname='active_nonzero_shape_key',
            rows=6
        )
        box.operator(MRF_OT_scan_nonzero_shape_keys.bl_idname, text="Refresh Nonzero ShapeKeys")
        if is_fake:
            layout.enabled = False
        
        

classes = [
    MRF_UL_control_item,
    MRF_UL_shape_key_item,
    MRF_PT_face_control_panel,
    
]   
            

def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)


if __name__ == '__main__':
    register()
