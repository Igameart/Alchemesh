import bpy
from .dropdown import dropdown
from ..operators.fit_bones_via_mod import (
    MRF_OT_fit_bones,
    MRF_OT_init_mesh_deform_proxy,
    MRF_OT_init_surface_deform_proxy
)
from ..operators.auto_fit_bones import MRF_OT_auto_fit_bones
from ..operators.fit_bones_2 import MRF_OT_fit_bones_with_wrt
from ..operators.fit_geo_center import MRF_OT_fit_geo_center
from ..operators.interpolate_bones import MRF_OT_interpolate_bones


class MRF_PT_armature_edit(bpy.types.Panel):
    """
    Addon main menu (N-Panel)
    """
    bl_label = 'MetaReForge'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MRF"
    bl_context = 'armature_edit'

    
    def draw(self, context):
        layout = self.layout
        config = context.scene.meta_reforge_config
        if context.active_object is not None and context.active_object is not config.edit_armature.final_object:
            layout.label(text="Final armature should be active")
            return
        section = layout.box()
        if dropdown(section, config.view_group, "show_auto_fit_section", "Auto-Fit", icon="ARMATURE_DATA"):
            section.prop(config, "auto_fit_config", text="Config")
            props = section.operator(MRF_OT_auto_fit_bones.bl_idname, text="Auto")
            props.config_path = config.auto_fit_config
        section = layout.box()
        if dropdown(section, config.view_group, "show_fit_bones_advanced", "Advanced Fit", icon="BONE_DATA"):
            basis_mesh = config.fit_bones_basis_mesh
            final_mesh = config.fit_bones_final_mesh
            basis_armature = config.fit_bones_basis_armature
            section.prop(config, "fit_bones_basis_armature", text="Initial Arm")
            section.prop(config, "fit_bones_basis_mesh", text="Initial Mesh")
            section.prop(config, "fit_bones_final_mesh", text="Final Mesh")
            section.prop(config, "fit_bones_lock_rotation", text="Keep Original Rotation")
            # SURFACE DEFORM FIT
            box = section.box()
            lock_rotation = config.fit_bones_lock_rotation
            box.label(text="Surface Deform:", icon="MOD_MESHDEFORM")
            box.prop(config, "surface_deform_falloff", text="Falloff", slider=True)
            SD_PROXY_DEFAULT_NAME = "MRF_SD_PROXY"
            proxy = bpy.data.objects.get(SD_PROXY_DEFAULT_NAME, None)
            sd_init_row = box.row()
            props = sd_init_row.operator(
                MRF_OT_init_surface_deform_proxy.bl_idname,
                text="Init Proxy" if proxy is None else "Re-init Proxy"
            )
            if basis_mesh and final_mesh and basis_armature:
                props.basis_mesh_name = basis_mesh.name
                props.basis_armature_name = basis_armature.name
                props.falloff = config.surface_deform_falloff
                props.proxy_name = SD_PROXY_DEFAULT_NAME
            else:
                sd_init_row.enabled = False
            sd_fit_row = box.row()
            props = sd_fit_row.operator(MRF_OT_fit_bones.bl_idname, text="Fit Selected")
            if basis_mesh and final_mesh and basis_armature and proxy:
                props.basis_mesh_name = basis_mesh.name
                props.final_mesh_name = final_mesh.name
                props.basis_armature_name = basis_armature.name
                props.proxy_name = SD_PROXY_DEFAULT_NAME
                props.lock_rotation = lock_rotation
            else:
                sd_fit_row.enabled = False
                
            # Mesh deform
            box = section.box()
            box.label(text="Mesh Deform:", icon="MOD_MESHDEFORM")
            box.prop(config, "mesh_deform_precision", text="Precision", slider=True)
            MD_PROXY_DEFAULT_NAME = "MRF_MD_PROXY"
            proxy = bpy.data.objects.get(MD_PROXY_DEFAULT_NAME, None)
            md_init_row = box.row()
            props = md_init_row.operator(
                MRF_OT_init_mesh_deform_proxy.bl_idname,
                text="Init Proxy" if proxy is None else "Re-init Proxy"
            )
            if basis_mesh and final_mesh and basis_armature:
                props.basis_mesh_name = basis_mesh.name
                props.basis_armature_name = basis_armature.name
                props.precision = config.mesh_deform_precision
                props.proxy_name = MD_PROXY_DEFAULT_NAME
            else:
                md_init_row.enabled = False
            md_fit_row = box.row()
            props = md_fit_row.operator(MRF_OT_fit_bones.bl_idname, text="Fit Selected")
            if basis_mesh and final_mesh and basis_armature and proxy:
                props.basis_mesh_name = basis_mesh.name
                props.final_mesh_name = final_mesh.name
                props.basis_armature_name = basis_armature.name
                props.proxy_name = MD_PROXY_DEFAULT_NAME
                props.lock_rotation = lock_rotation
            else:
                sd_fit_row.enabled = False

            # Interpolate
            box = section.box()
            box.label(text="Interpolate:", icon="MOD_DATA_TRANSFER")
            box.prop_search(config, "origin_bone", context.active_object.data, "bones", text="Origin")
            box.prop_search(config, "end_bone", context.active_object.data, "bones", text="End")
            props = box.operator(MRF_OT_interpolate_bones.bl_idname, text="Interpolate Selected")
            props.origin_bone = config.origin_bone
            props.end_bone = config.end_bone
            # props.reference_armature = config.initial_edit_armature.name
                
                

classes = [MRF_PT_armature_edit]   
            

def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)


if __name__ == '__main__':
    register()
