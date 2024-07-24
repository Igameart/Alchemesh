import bpy
from typing import Any
from ..operators.list_action import MRF_OT_list_action
from ..operators.select_object import MRF_OT_select_object
    

def draw_list_action(layout, propname: str, active_propname: str, data_propname: str = ""):
    op_props = []
    row = layout.row(align=False)
    split = row.split(factor=0.5, align=True)
    props = split.operator(MRF_OT_list_action.bl_idname, icon='ADD', text='')
    props.action = 'ADD'
    op_props.append(props)
    props = split.operator(MRF_OT_list_action.bl_idname, icon='REMOVE', text='')
    props.action = 'REMOVE'
    op_props.append(props)
    props = row.separator()
    split = row.split(factor=0.5, align=True)
    props = split.operator(MRF_OT_list_action.bl_idname, icon='TRIA_UP', text='')
    props.action = 'MOVE_UP'
    op_props.append(props)
    props = split.operator(MRF_OT_list_action.bl_idname, icon='TRIA_DOWN', text='')
    props.action = 'MOVE_DOWN'
    op_props.append(props)
    
    for props in op_props:
        props.propname = propname
        props.active_propname = active_propname
        props.data_propname = data_propname


def draw_mesh_item_details(layout, item):
    box = layout.box()
    box.label(text="Item Details:")
    box.prop(item, "basis_object", text="Basis")
    row = box.row(align=True)
    row.prop(item, "final_object", text="Final")
    if item.final_object:
        row.operator(MRF_OT_select_object.bl_idname, text="", icon="RESTRICT_SELECT_OFF").object_name = item.final_object.name
    box.prop(item, "edit_id", text="Edit ID")


def draw_lod_item(layout: bpy.types.UILayout, item, index: int):
    row = layout.row()   
    row.label(text=f"LOD{index}")


def draw_mesh_item(layout: bpy.types.UILayout, item):
    row = layout.row()
    row.label(text=item.final_object.name if item.final_object else "NOT DEFINED")


class MRF_UL_head_lod_items(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        draw_lod_item(layout, item, index)


class MRF_UL_head_mesh_items(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        draw_mesh_item(layout, item)


class MRF_UL_body_lod_items(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        draw_lod_item(layout, item, index)


class MRF_UL_body_mesh_items(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        draw_mesh_item(layout, item)

    
class MRF_UL_shape_key_items(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        row.prop(item, 'checked', text='')

        split = row.split(factor=0.7, align=True)
        split.label(text=item.shape_key_name, icon='SHAPEKEY_DATA')
        split.prop(item, 'lod_limit', text="")
        if not item.checked:
            split.enabled = False

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

class MRF_UL_cloth_items(bpy.types.UI_UL_list):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        row.label(text=item.item_name)

class MRF_UL_cloth_lod_items(bpy.types.UI_UL_list):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        row.label(text=f"LOD{index}")


def draw_head_lods_list_view(
        layout: bpy.types.UILayout,
        config,
        rows: int = 5,
        maxrows: int = 5
    ) -> None:
    col = layout.column(align=True)
    col.label(text="Levels of Detail:")
    col.template_list(
        listtype_name="MRF_UL_head_lod_items", list_id="",
        dataptr=config, propname="fbx_head_lods",
        active_dataptr=config, active_propname="fbx_head_active_lod",
        rows=rows, maxrows=maxrows
    )

    draw_list_action(col, propname="fbx_head_lods", active_propname="fbx_head_active_lod")

    if config.fbx_head_active_lod < len(config.fbx_head_lods):
        active_item = config.fbx_head_lods[config.fbx_head_active_lod]
        col = layout.column(align=True)
        col.label(text="Objects:")
        col.template_list(
            listtype_name="MRF_UL_head_mesh_items", list_id="",
            dataptr=active_item, propname="mesh_items",
            active_dataptr=active_item, active_propname="active_index",
            rows=rows, maxrows=maxrows
        )
        data_propname = f"fbx_head_lods[{config.fbx_head_active_lod}]"
        draw_list_action(col, data_propname=data_propname, propname="mesh_items", active_propname="active_item")
        if active_item.active_index < len(active_item.mesh_items):
            mesh_item = active_item.mesh_items[active_item.active_index]
            draw_mesh_item_details(layout, mesh_item)


def draw_body_lods_list_view(
        layout: bpy.types.UILayout,
        config,
        rows: int = 5,
        maxrows: int = 5
    ) -> None:
    col = layout.column(align=True)
    col.label(text="Levels of Detail:")
    col.template_list(
        listtype_name="MRF_UL_body_lod_items", list_id="",
        dataptr=config, propname="fbx_body_lods",
        active_dataptr=config, active_propname="fbx_body_active_lod",
        rows=rows, maxrows=maxrows
    )

    draw_list_action(col, propname="fbx_body_lods", active_propname="fbx_body_active_lod")

    if config.fbx_body_active_lod < len(config.fbx_body_lods):
        active_item = config.fbx_body_lods[config.fbx_body_active_lod]
        col = layout.column(align=True)
        col.label(text="Objects:")
        col.template_list(
            listtype_name="MRF_UL_body_mesh_items", list_id="",
            dataptr=active_item, propname="mesh_items",
            active_dataptr=active_item, active_propname="active_index",
            rows=rows, maxrows=maxrows
        )
        data_propname = f"fbx_body_lods[{config.fbx_body_active_lod}]"
        draw_list_action(col, data_propname=data_propname, propname="mesh_items", active_propname="active_item")
        if active_item.active_index < len(active_item.mesh_items):
            mesh_item = active_item.mesh_items[active_item.active_index]
            draw_mesh_item_details(layout, mesh_item)


def draw_clothes_list_view(
        layout: bpy.types.UILayout,
        config,
        rows: int = 5,
        maxrows: int = 5
    ) -> None:
    col = layout.column(align=True)
    col.label(text="Clothes:")
    col.template_list(
        listtype_name="MRF_UL_cloth_items", list_id="",
        dataptr=config, propname="cloth_items",
        active_dataptr=config, active_propname="active_cloth_item",
        rows=rows, maxrows=maxrows
    )
    draw_list_action(col, propname="cloth_items", active_propname="active_cloth_item")

    if config.active_cloth_item < len(config.cloth_items):
        active_item = config.cloth_items[config.active_cloth_item]
        layout.prop(active_item, "item_name", text="Name")
        layout.prop(active_item, "armature", text="Armature")
        col = layout.column(align=True)
        col.label(text="LODs:")
        col.template_list(
            listtype_name="MRF_UL_cloth_lod_items", list_id="",
            dataptr=active_item, propname="lod_items",
            active_dataptr=active_item, active_propname="active_lod_index",
            rows=rows, maxrows=maxrows
        )
        data_propname = f"cloth_items[{config.active_cloth_item}]"
        draw_list_action(col, data_propname=data_propname, propname="lod_items", active_propname="active_lod_index")
        if active_item.active_lod_index < len(active_item.lod_items):
            mesh_item = active_item.lod_items[active_item.active_lod_index]
            draw_mesh_item_details(layout, mesh_item)


classes = [
    MRF_UL_head_lod_items,
    MRF_UL_body_lod_items,
    MRF_UL_cloth_items,
    MRF_UL_cloth_lod_items,
    MRF_UL_head_mesh_items,
    MRF_UL_body_mesh_items,
    MRF_UL_shape_key_items
]

def register():
    for cl in classes:
        bpy.utils.register_class(cl)


def unregister():
    for cl in classes:
        bpy.utils.unregister_class(cl)
