from ..dna import dna_export
from . import (
    mh_import,
    install_dnacalib,
    setup_scene,
    mh_export,
    fit_bones_via_mod,
    reset_split_normals,
    init_objects,
    fit_bones_2,
    fit_geo_center,
    auto_fit_bones,
    open_directory,
    synchronize,
    picker,
    interpolate_bones,
    control_rig,
    control_rig_config,
    list_action,
    select_object,
    fit_edit_mesh,
    update_shape_keys,
    validate_mesh
)


modules = [
    install_dnacalib,
    setup_scene,
    mh_import,
    mh_export,
    fit_bones_via_mod,
    dna_export, 
    reset_split_normals,
    init_objects,
    fit_bones_2,
    fit_geo_center,
    auto_fit_bones,
    open_directory,
    synchronize,
    picker,
    interpolate_bones,
    control_rig,
    control_rig_config,
    list_action,
    select_object,
    fit_edit_mesh,
    update_shape_keys,
    validate_mesh
]

def register():
    for module in modules:
        module.register()


def unregister():
    for module in modules:
        module.unregister()
