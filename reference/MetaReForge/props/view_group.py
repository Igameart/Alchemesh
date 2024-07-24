import bpy


class MRF_ViewPropertyGroup(bpy.types.PropertyGroup):
    # GUI Properties
    show_head_objects: bpy.props.BoolProperty(name="Show Head Objects", default=False)
    show_body_objects: bpy.props.BoolProperty(name="Show Body Objects", default=False)
    show_cloth_objects: bpy.props.BoolProperty(name="Show Cloth Objects", default=False)
    show_import_section: bpy.props.BoolProperty(name="Show FBX Section", default=True)
    show_picker_section: bpy.props.BoolProperty(name="Show Mesh Picker", default=False)
    show_edit_section: bpy.props.BoolProperty(name="Show Edit Section", default=False)
    show_update_section: bpy.props.BoolProperty(name="Show Update Section", default=False)
    show_export_section: bpy.props.BoolProperty(name="Show Export Section", default=False)
    
    show_fit_bones_advanced: bpy.props.BoolProperty(name="Show Advanced Fit Bones Section", default=False)
    show_auto_fit_section: bpy.props.BoolProperty(name="Show Auto-Fit Bones Section", default=True)
    export_progress: bpy.props.FloatProperty(name="Progress", default=0, min=0, max=100, subtype="PERCENTAGE")
    export_running: bpy.props.BoolProperty(name="Export Running", default=False)


def register():
    bpy.utils.register_class(MRF_ViewPropertyGroup)


def unregister():
    bpy.utils.unregister_class(MRF_ViewPropertyGroup)
