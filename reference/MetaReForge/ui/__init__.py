from . import (
    armature_edit_panel,
    object_panel,
    prefs,
    edit_mesh_list_view,
    list_view,
    face_control_panel
)


modules = [
    armature_edit_panel,
    edit_mesh_list_view,
    list_view,
    object_panel,
    prefs,
    face_control_panel
]


def register():
    for module in modules:
        module.register()


def unregister():
    for module in modules:
        module.unregister()
