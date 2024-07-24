import bpy
from .dropdown import dropdown
from ..dna.dna_export import MRF_OT_write_dna
from ..dna.libimport import DNA_IMPORT_EX, is_fake
from ..operators.setup_scene import MRF_OT_setup_scene
from ..utils.blender.unsorted import check_scene_units
from ..operators.mh_import import (
    MRF_OT_import,
    MRF_OT_import_cloth,
    check_for_import,
    check_for_import_cloth,
    check_for_dna_export
)
from ..operators.validate_mesh import MRF_OT_validate_edit_meshes_edges
from ..operators.mh_export import MRF_OT_export_fbx
from ..operators.reset_split_normals import MRF_OT_recompute_split_normals
from ..operators.init_objects import MRF_OT_init_objects
from ..operators.synchronize import MRF_OT_synchronize, MRF_OT_update_shape_keys_to_sync
from .edit_mesh_list_view import draw_edit_meshes_list_view
from .list_view import draw_body_lods_list_view, draw_head_lods_list_view, draw_clothes_list_view
from ..operators.picker import MRF_OT_view_picker
from .. import icons


class MRF_PT_object_mode(bpy.types.Panel):
    """
    Addon main menu (N-Panel)
    """
    bl_label = 'MetaReForge'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MRF"
    bl_context = 'objectmode'

    def draw(self, context):
        layout = self.layout

        # layout.row().template_icon(icon_value=icons.get_icon("MRF_LOGO"), scale=6.0)
        config = context.scene.meta_reforge_config
        is_units_ok = check_scene_units(context.scene)
        if not is_units_ok:
            layout.operator(MRF_OT_setup_scene.bl_idname, text="Setup scene!")

        # VIEW SECTION
        box = layout.box()
        if dropdown(box, config.view_group, "show_picker_section", "View", icon_value=icons.get_icon("MRF_VIEW")):
            box.prop(config, "show_armature", toggle=True, icon="OUTLINER_OB_ARMATURE")
            col = box.column(align=True)
            if len(config.edit_meshes) > 0:
                props = col.operator(MRF_OT_view_picker.bl_idname, text="Edit Shape", icon="OUTLINER_OB_MESH")
                props.option = "FINAL_SHAPE"
                props.show_armature = config.show_armature

            if config.max_num_lods != 0:
                grid = col.grid_flow(row_major=True, columns=2, even_columns=False, even_rows=False, align=True)
                for idx in range(config.max_num_lods):
                    props = grid.operator(MRF_OT_view_picker.bl_idname, text=f"LOD{idx}", icon="OUTLINER_OB_MESH")
                    props.option = f"LOD_{idx}"
                    props.show_armature = config.show_armature
        
        # IMPORT SECTION
        box = layout.box()
        if dropdown(box, config.view_group, "show_import_section", "Import", icon_value=icons.get_icon("MRF_IMPORT")):
            row = box.row(align=True)
            row.prop(config, "import_head", toggle=1)
            row.prop(config, "import_body", toggle=1)
            row = box.row()
            row.prop(config, "fbx_head_path", text="Head FBX")
            if not config.import_head or config.build_head_from_dna:
                row.enabled = False
            row = box.row()
            row.prop(config, "fbx_body_path", text="Body FBX")
            if not config.import_body:
                row.enabled = False
            dna_col = box.column()
            dna_col.prop(config, "dna_path", text="DNA", icon="RNA")
            if DNA_IMPORT_EX is not None:
                dna_col.label(text="DNACalib is not linked", icon="ERROR")
                dna_col.enabled = False
            
            row = box.row()
            row.prop(config, "build_head_from_dna", text="Build Head from DNA")
            if not config.import_head:
                row.enabled = False

            if config.build_head_from_dna:
                box.prop(config, "build_head_morph_threshold", text="Morph Thresh.")
                                
            # box.prop(config, "import_lod0_only", text="LOD0 Only")
            can_import, error = check_for_import(context)
            if can_import and is_units_ok:
                box.operator(MRF_OT_import.bl_idname)
            else:
                error = error if is_units_ok else "Setup scene units!"
            
                col = box.column(align=True)
                col.operator(MRF_OT_import.bl_idname)
                col.label(text=error)
                col.enabled = False
                
        # Showing head lods and armature
        box = layout.box()
        if dropdown(box, config.view_group, "show_head_objects", "Head Objects", icon_value=icons.get_icon("MRF_FEM_HEAD")):
            box.column().prop(config, "fbx_head_armature", text="Armature")
            col = box.column()
            draw_head_lods_list_view(col, config, rows=2, maxrows=4)

        # Showing body lods and armature
        box = layout.box()
        if dropdown(box, config.view_group, "show_body_objects", "Body Objects", icon_value=icons.get_icon("MRF_FEM_BODY")):
            box.column().prop(config, "fbx_body_armature", text="Armature")
            col = box.column()
            draw_body_lods_list_view(col, config, rows=2, maxrows=4)

        box = layout.box()
        if dropdown(box, config.view_group, "show_cloth_objects", "Cloth Objects", icon_value=icons.get_icon("MRF_T_SHIRT")):
            box.prop(config, "cloth_import_path", text="Path")

            can_import, error = check_for_import_cloth(context)
            row = box.row()
            row.operator(MRF_OT_import_cloth.bl_idname, text="Import")
            if not can_import:
                box.label(text=f"{error}")
                row.enabled = False
            draw_clothes_list_view(box, config=config, rows=2, maxrows=4) 
        
        box = layout.box()
        if dropdown(box, config.view_group, "show_edit_section", "Edit Shape", icon_value=icons.get_icon("MRF_EDIT_CHARACTER")):
            # Init operator
            b = box.box()
            b.prop(config, "edit_mesh_merge_distance", text="Weld Distance")
            b.prop(config, "final_mesh_keep_shape_keys", text="Keep ShapeKeys")
            b.prop(config, "edit_mesh_tris_to_quads", text="Tris2Quads")
            col = b.column(align=True)
            props = col.operator(MRF_OT_init_objects.bl_idname, text="Initialize")
            col.operator(MRF_OT_validate_edit_meshes_edges.bl_idname, text="Validate Edges")
            # col.operator(MRF_OT_validate_edit_meshes_faces.bl_idname, text="Validate Faces")
            props.merge_distance = config.edit_mesh_merge_distance
            props.keep_shape_keys = config.final_mesh_keep_shape_keys
            props.tris_to_quads - config.edit_mesh_tris_to_quads

            # Initialized objects
            box.label(text="Armature:", icon="ARMATURE_DATA")
            box.prop(config.edit_armature, "basis_object", text="Basis")
            box.prop(config.edit_armature, "final_object", text="Final")
            box.label(text="Meshes:", icon="MESH_DATA")
            
            draw_edit_meshes_list_view(box, config=config, rows=2, maxrows=4)

        # SYNCHRONYZE
        box = layout.box()
        if dropdown(box, config.view_group, "show_update_section", "Update Original", icon_value=icons.get_icon("MRF_SYNC")):
            b = box.box()
            b.prop(config, "sync_use_noise")
            if config.sync_use_noise:
                b.prop(config, "sync_noise_min_value", text="Min")
                b.prop(config, "sync_noise_max_value", text="Max")

            col = b.column(align=True)
            col.label(text="Shape Keys:")
            col.template_list(
                'MRF_UL_shape_key_items', '',
                config, 'sync_shape_keys_to_transfer',
                config, 'sync_active_shape_key',
                rows=5
            )
            op_props = col.operator(MRF_OT_update_shape_keys_to_sync.bl_idname, text='Refresh')
            op_props.reset = False
            row = col.row(align=True)
            op_props = row.operator(MRF_OT_update_shape_keys_to_sync.bl_idname, text='Check All')
            op_props.reset = True
            op_props.reset_value = True
            op_props = row.operator(MRF_OT_update_shape_keys_to_sync.bl_idname, text='Uncheck All')
            op_props.reset = True
            op_props.reset_value = False


            row = b.row(align=True)
            row.prop(config, "sync_head", toggle=1, text="Head")
            row.prop(config, "sync_body", toggle=1, text="Body")
            row.prop(config, "sync_clothes", toggle=1, text="Clothes")
            props = b.operator(MRF_OT_synchronize.bl_idname, text="Synchronize")
            props.use_noise = config.sync_use_noise
            props.noise_min_value = config.sync_noise_min_value
            props.noise_max_value = config.sync_noise_max_value
            props.sync_head = config.sync_head
            props.sync_body = config.sync_body
            props.sync_clothes = config.sync_clothes

            b = box.box()
            
            # Recalculate split normals
            b.prop(config, "split_normals_align_vertices", text="Align Vertices")
            b.prop(config, "split_normals_weld_distance", text="Weld Distance")
            op_props = b.operator(MRF_OT_recompute_split_normals.bl_idname, icon="NORMALS_VERTEX_FACE")
            op_props.weld_distance = config.split_normals_weld_distance
            op_props.align_vertices = config.split_normals_align_vertices
            
        
        box = layout.box()
        if dropdown(box, config.view_group, "show_export_section", "Export", icon_value=icons.get_icon("MRF_EXPORT")):
            box.prop(config, "export_name", text="Name")
            col = box.column(align=True)
            col.label(text=f"Output path:")
            col.prop(config, "output_path", text="")

            row = box.row(align=True)
            row.prop(config, "fbx_export_head", toggle=1, text="Head")
            row.prop(config, "fbx_export_body", toggle=1, text="Body")
            row.prop(config, "fbx_export_clothes", toggle=1, text="Clothes")

            col = box.column(align=True)
            row = col.row()

            if config.view_group.export_running:
                row.prop(config.view_group, "export_progress", text=f"Exporting...", slider=True)
                row.enabled = False
            else:
                row.operator(MRF_OT_export_fbx.bl_idname)

            row = col.row()
            
            if DNA_IMPORT_EX is not None:
                row.enabled = False
                col.label(text="DNA-Calibration is not linked")
                row.prop(config, "dummy_bool", text="Modify DNA", toggle=1)
            elif not config.edit_armature.final_object:
                row.enabled = False
                row.operator(MRF_OT_write_dna.bl_idname, text="Modify DNA")
                col.label(text="No final armature")
            else:  
                row.operator(MRF_OT_write_dna.bl_idname, text="Modify DNA")
                enabled, reason = check_for_dna_export(context)
                if not enabled:
                    row.enabled = False
                    col.label(text=reason)
            

def register():
    bpy.utils.register_class(MRF_PT_object_mode)


def unregister():
    bpy.utils.unregister_class(MRF_PT_object_mode)


if __name__ == '__main__':
    register()
