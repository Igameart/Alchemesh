import bpy
from .list_view import draw_list_action
from ..operators.select_object import MRF_OT_select_object
from ..operators.fit_edit_mesh import MRF_OT_transfer_shape, MRF_OT_transfer_shape_target_from_id
from .dropdown import dropdown


def draw_edit_mesh_item_details(layout, config, item):
    box = layout.box()
    if dropdown(box, config, attribute="edit_mesh_show_details", text="Item Details:"):
        box.prop(item, "basis_object", text="Basis")
        row = box.row(align=True)
        row.prop(item, "final_object", text="Final")
        if item.final_object:
            row.operator(MRF_OT_select_object.bl_idname, text="", icon="RESTRICT_SELECT_OFF").object_name = item.final_object.name
        box.prop(item, "edit_id", text="Edit ID")
    if dropdown(box, config, attribute="emt_show", text="Transfer Shape:"):
        row = box.row(align=True)
        row.prop(config, "emt_edit_id", text="edit_id")
        row.operator(MRF_OT_transfer_shape_target_from_id.bl_idname, text="", icon="SORT_ASC")
        box.prop(config, "emt_source_basis", text="Basis")
        box.prop(config, "emt_source_final", text="Final")
        box.prop(config, "emt_laplacian_enabled", text="Use Laplacian Deform")
        col = box.column()
        col.prop(config, "emt_laplacian_iterations", text="Lapl. Iterations")
        col.prop(config, "emt_laplacian_threshold", text="Lapl. Thresh")
        col.enabled = config.emt_laplacian_enabled
        row = box.column()
        op_props = row.operator(MRF_OT_transfer_shape.bl_idname, text="Transfer")
        src_basis = config.emt_source_basis
        src_final = config.emt_source_final
        if src_basis and src_final and item.final_object and item.basis_object:
            op_props.source_basis = src_basis.name
            op_props.source_final = src_final.name
            op_props.target_basis = item.basis_object.name
            op_props.target = item.final_object.name
            op_props.laplacian_iterations = config.emt_laplacian_iterations if config.emt_laplacian_enabled else 0
            op_props.laplacian_threshold = config.emt_laplacian_threshold
        else:
            row.enabled = False


class MRF_UL_edit_mesh_items(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        obj = item.final_object
        
        if obj:
            row.label(text=obj.name, icon="MESH_DATA")
            op_props = row.operator(MRF_OT_select_object.bl_idname, text="", icon="RESTRICT_SELECT_OFF")
            op_props.object_name = item.final_object.name
        else:
            row.label(text="NONE", icon="MESH_DATA")
            op_props = row.operator(MRF_OT_select_object.bl_idname, text="", icon="RESTRICT_SELECT_OFF")
            row.enabled = False


def draw_edit_meshes_list_view(
        layout: bpy.types.UILayout,
        config,
        rows: int = 5,
        maxrows: int = 5
    ):
    col = layout.column(align=True)
    col.template_list(
        listtype_name="MRF_UL_edit_mesh_items", list_id="",
        dataptr=config, propname="edit_meshes",
        active_dataptr=config, active_propname="edit_mesh_active_index",
        rows=rows, maxrows=maxrows
    )
    draw_list_action(col, propname="edit_meshes", active_propname="edit_mesh_active_index")
    if config.edit_mesh_active_index < len(config.edit_meshes):
        mesh_item = config.edit_meshes[config.edit_mesh_active_index]
        draw_edit_mesh_item_details(layout, config, mesh_item)


def register():
    bpy.utils.register_class(MRF_UL_edit_mesh_items)


def unregister():
    bpy.utils.unregister_class(MRF_UL_edit_mesh_items)
