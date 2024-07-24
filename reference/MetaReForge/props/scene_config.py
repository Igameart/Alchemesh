import os
import bpy
from .poll import poll_armature, poll_mesh
from .items import (
    MRF_object_shape_key_item,
    MRF_shape_key_item,
    MRF_mesh_item,
    MRF_edit_armature,
    MRF_level_of_detail,
    MRF_cloth_item
)
from .view_group import MRF_ViewPropertyGroup
from ..globals import AUTO_FIT_CONFIG_DIRECTORY
from ..utils.blender.object import ensure_objects_visible
from bpy.app.handlers import persistent


# Callback function for the EnumProperty to dynamically get items
def update_auto_fit_items(self, context):
    files = []
    for file in os.listdir(AUTO_FIT_CONFIG_DIRECTORY):
        if file.endswith(".json"):
            # Strip the extension for display
            name_without_extension = os.path.splitext(file)[0]
            item = (os.path.join(AUTO_FIT_CONFIG_DIRECTORY, file), name_without_extension, "")
            # Add the tuple (identifier, name, description)
            if name_without_extension == "metahuman_default":
                files.insert(0, item)
            else:
                files.append(item)
    
    return files

def update_armature_bool(self, context):
    config = context.scene.meta_reforge_config
    objects = []
    if config.edit_armature.final_object:
        objects.append(config.edit_armature.final_object)
    if config.fbx_head_armature:
        objects.append(config.fbx_head_armature)
    if config.fbx_body_armature:
        objects.append(config.fbx_body_armature)
    for obj in objects:
        try:
            obj.hide_set(not self.show_armature)
        except RuntimeError:
            pass



class MRF_scene_config(bpy.types.PropertyGroup):
    dummy_bool: bpy.props.BoolProperty(default=False)
    view_group: bpy.props.PointerProperty(type=MRF_ViewPropertyGroup)

    show_armature: bpy.props.BoolProperty(
        name="Show Armature",
        default=True,
        update=update_armature_bool,
        description="Show or hide the metahuman armature"
    )

    # Import
    dna_path: bpy.props.StringProperty(
        name="DNA Path",
        subtype="FILE_PATH",
        description=(
            "Path to DNA file. Usual location C:/Users/<USER_NAME>/Documents/Megascans Library/"
            "Downloaded/UAssets/<ASSET_ID>/Tier0/asset_ue/MetaHumans/<METAHUMAN_NAME>/SourceAssets"
        )
    )
    import_head: bpy.props.BoolProperty(name="Import Head", default=True)
    import_body: bpy.props.BoolProperty(name="Import Body", default=True)
    fbx_head_path: bpy.props.StringProperty(name="FBX Head Path", subtype="FILE_PATH")
    fbx_body_path: bpy.props.StringProperty(name="FBX Body Path", subtype="FILE_PATH")
    import_lod0_only: bpy.props.BoolProperty(
        name="LOD0 Only",
        default=False,
    description="Removes all LODs except the lowest"
    )
    build_head_from_dna: bpy.props.BoolProperty(
        name="Head from DNA",
        default=True,
        description="Build head meshes and armature from DNA file instead of FBX"
    )
    build_head_morph_threshold: bpy.props.FloatProperty(
        name="Morph Threshould Position",
        default=0.015, precision=4,
        description="Threshold to compare vertex position equality when computing morph target deltas"
    )

    # EXPORT PROPS
    output_path: bpy.props.StringProperty(name="Output Path", subtype="DIR_PATH", default="//")
    export_name: bpy.props.StringProperty(name="Name", default="default_name")
    fbx_export_head: bpy.props.BoolProperty(name="Export Head", default=True)
    fbx_export_body: bpy.props.BoolProperty(name="Export Body", default=True)
    fbx_export_clothes: bpy.props.BoolProperty(name="Export Clothes", default=True)
    export_dna: bpy.props.BoolProperty(name="Export DNA", default=True)


    fbx_head_armature: bpy.props.PointerProperty(name="Head Armature", type=bpy.types.Object, poll=poll_armature)
    fbx_head_lods: bpy.props.CollectionProperty(type=MRF_level_of_detail)
    fbx_head_active_lod: bpy.props.IntProperty(default=0)
    fbx_head_override_bone_length: bpy.props.BoolProperty(name="Set Bone Length", default=True)
    fbx_head_bone_length: bpy.props.FloatProperty(name="Bone Length", default=1)
    # FBX body props
    fbx_body_armature: bpy.props.PointerProperty(name="Armature Object", type=bpy.types.Object, poll=poll_armature)
    fbx_body_lods: bpy.props.CollectionProperty(type=MRF_level_of_detail)
    fbx_body_active_lod: bpy.props.IntProperty(default=0)
    fbx_body_override_bone_length: bpy.props.BoolProperty(name="Set Bone Length", default=True)
    fbx_body_bone_length: bpy.props.FloatProperty(name="Bone Length", default=1)

    # CLOTHES PROPS
    cloth_import_path: bpy.props.StringProperty(name="Cloth Import Path", subtype="FILE_PATH")
    cloth_export_path: bpy.props.StringProperty(name="Cloth Export Path", subtype="DIR_PATH", default="//")
    cloth_items: bpy.props.CollectionProperty(type=MRF_cloth_item)
    active_cloth_item: bpy.props.IntProperty()

    # Edit objects
    edit_meshes: bpy.props.CollectionProperty(name="Edit Meshes", type=MRF_mesh_item)
    edit_mesh_active_index: bpy.props.IntProperty(default=0)
    edit_armature: bpy.props.PointerProperty(name="Edit Armature", type=MRF_edit_armature)
    edit_mesh_show_details: bpy.props.BoolProperty(default=False)
    nonzero_shape_keys: bpy.props.CollectionProperty(name="Shape Keys", type=MRF_object_shape_key_item)
    active_nonzero_shape_key: bpy.props.IntProperty()
    
    # emt - Edit Mesh Transfer
    emt_show: bpy.props.BoolProperty(default=False)
    emt_edit_id: bpy.props.StringProperty(default="")
    emt_laplacian_enabled: bpy.props.BoolProperty(default=False)
    emt_laplacian_iterations: bpy.props.IntProperty(default=3, min=1, max=50)
    emt_laplacian_threshold: bpy.props.FloatProperty(name="Laplacian Anchor Threshold", default=0.2, precision=3)
    emt_source_basis: bpy.props.PointerProperty(type=bpy.types.Object, poll=poll_mesh)
    emt_source_final: bpy.props.PointerProperty(type=bpy.types.Object, poll=poll_mesh)
    emt_use_noise: bpy.props.BoolProperty(name="Use Noise", default=True)
    emt_noise_min_value: bpy.props.FloatProperty(
        name="Noise Min Value",
        default=3e-4,
        min=-1e-2,
        max=1e-2,
        step=10,
        precision=6
    )
    emt_noise_max_value: bpy.props.FloatProperty(
        name="Noise Max Value",
        default=6e-4,
        min=-1e-2,
        max=1e-2,
        step=100,
        precision=6
    )

    edit_mesh_merge_distance: bpy.props.FloatProperty(name="Edit Mesh Weld Distance", default=5e-4, precision=5)
    edit_mesh_tris_to_quads: bpy.props.BoolProperty(name="Tris to Quads", default=True)
    final_mesh_keep_shape_keys: bpy.props.BoolProperty(name="Edit Mesh Keep Shape Keys", default=False)
    
    split_normals_align_vertices: bpy.props.BoolProperty(name="Allign Vertices", default=True)
    split_normals_weld_distance: bpy.props.FloatProperty(name="Weld Distance", default=5e-3, precision=5)

    # Fit bones
    surface_deform_falloff: bpy.props.FloatProperty(name="Falloff", description="Surface Deform Fallof", min=2, max=16, default=4)
    mesh_deform_precision: bpy.props.IntProperty(name="Precision", description="The grid size for binding", min=2, max=10, default=4)
    fit_bones_basis_mesh: bpy.props.PointerProperty(name="Fit Bones Basis Mesh", type=bpy.types.Object, poll=poll_mesh)
    fit_bones_final_mesh: bpy.props.PointerProperty(name="Fit Bones Final Mesh", type=bpy.types.Object, poll=poll_mesh)
    fit_bones_basis_armature: bpy.props.PointerProperty(name="Fit Bones Basis Armature", type=bpy.types.Object, poll=poll_armature)
    fit_bones_lock_rotation: bpy.props.BoolProperty(name="Fit Bones Lock Rotation", default=False)
    fit_geo_target_mesh: bpy.props.PointerProperty(name="Geo Target Mesh", type=bpy.types.Object, poll=poll_mesh)

    sync_enable_shape_keys: bpy.props.BoolProperty(name="Transfer Shape Keys", default=False)
    sync_shape_keys_to_transfer: bpy.props.CollectionProperty(
        name="Shape Keys to Transfer",
        type=MRF_shape_key_item
    )
    sync_active_shape_key: bpy.props.IntProperty(name="Active Shape Key")
    sync_use_noise: bpy.props.BoolProperty(name="Use Noise", default=True)
    sync_noise_min_value: bpy.props.FloatProperty(
        name="Noise Min Value",
        default=3e-4,
        min=-1e-2,
        max=1e-2,
        step=10,
        precision=6
    )
    sync_noise_max_value: bpy.props.FloatProperty(
        name="Noise Max Value",
        default=6e-4,
        min=-1e-2,
        max=1e-2,
        step=100,
        precision=6
    )
    sync_head: bpy.props.BoolProperty(default=True, description="Synchronize Head")
    sync_body: bpy.props.BoolProperty(default=True, description="Synchronize Body")
    sync_clothes: bpy.props.BoolProperty(default=True, description="Synchronize Clothes")

    # interpolate bone proportions
    origin_bone: bpy.props.StringProperty(name="Origin Bone")
    end_bone: bpy.props.StringProperty(name="End Bone")

    auto_fit_config: bpy.props.EnumProperty(items=update_auto_fit_items, name="Auto-Fit Config ", description="Choose a auto-fit config file")
    

    def prepare_objects(self, context: bpy.types.Context) -> None:
        ensure_objects_visible(self.get_associated_objects())
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

    @property
    def absolute_dna_path(self) -> str:
        return bpy.path.abspath(self.dna_path)
    
    @property
    def absolute_output_path(self) -> str:
        return bpy.path.abspath(self.output_path)
    
    def get_fbx_head_final_objects(self) -> list:
        result = list()
        if len(self.fbx_head_lods) != 0:
            for lod_item in self.fbx_head_lods:
                for mesh_item in lod_item.mesh_items:
                    if mesh_item.final_object:
                        result.append(mesh_item.final_object)
        return result
    
    def get_fbx_head_basis_objects(self) -> list:
        result = list()
        if len(self.fbx_head_lods) != 0:
            for lod_item in self.fbx_head_lods:
                for mesh_item in lod_item.mesh_items:
                    if mesh_item.basis_object:
                        result.append(mesh_item.basis_object)
        return result
    
    def get_fbx_body_final_objects(self) -> list:
        result = list()
        if len(self.fbx_body_lods) != 0:
            for lod_item in self.fbx_body_lods:
                for mesh_item in lod_item.mesh_items:
                    if mesh_item.final_object:
                        result.append(mesh_item.final_object)
        return result

    def get_fbx_body_basis_objects(self) -> list:
        result = list()
        if len(self.fbx_body_lods) != 0:
            for lod_item in self.fbx_body_lods:
                for mesh_item in lod_item.mesh_items:
                    if mesh_item.basis_object:
                        result.append(mesh_item.basis_object)
        return result
    
    def get_initial_edit_meshes(self) -> list:
        result = []
        for item in self.edit_meshes:
            if item.basis_object:
                result.append(item.basis_object)
        return result

    def get_final_edit_meshes(self) -> list:
        result = []
        for item in self.edit_meshes:
            if item.final_object:
                result.append(item.final_object)
        return result
    
    def get_cloth_objects(self) -> list:
        result = []
        for cloth_item in self.cloth_items:
            if cloth_item.armature:
                result.append(cloth_item.armature)
            for mesh_item in cloth_item.lod_items:
                if mesh_item.final_object:
                    result.append(mesh_item.final_object)
                if mesh_item.basis_object:
                    result.append(mesh_item.basis_object)
        return result
    
    def get_associated_objects(self) -> list:
        result = []
        result += self.get_fbx_head_final_objects()
        result += self.get_fbx_head_basis_objects()
        result += self.get_fbx_body_final_objects()
        result += self.get_fbx_body_basis_objects()
        result += self.get_initial_edit_meshes()
        result += self.get_final_edit_meshes()
        result += self.get_cloth_objects()
        if self.fbx_body_armature:
            result.append(self.fbx_body_armature)
        if self.fbx_head_armature:
            result.append(self.fbx_head_armature)

        if self.edit_armature:
            if self.edit_armature.basis_object:
                result.append(self.edit_armature.basis_object)
            if self.edit_armature.final_object:
                result.append(self.edit_armature.final_object)
        
        return result
    
    @property
    def max_num_lods(self) -> int:
        return max(len(self.fbx_head_lods), len(self.fbx_body_lods))
    

_prev_active_object = None


@persistent
def selection_changed(scene):
    global _prev_active_object
    obj = bpy.context.active_object
    if obj and obj is not _prev_active_object:
        _prev_active_object = obj
        config = scene.meta_reforge_config
        for idx, mesh_item in enumerate(config.edit_meshes):
            if obj is mesh_item.final_object:
                config.edit_mesh_active_index = idx
                return


def register():
    bpy.utils.register_class(MRF_scene_config)
    bpy.types.Scene.meta_reforge_config = bpy.props.PointerProperty(type=MRF_scene_config)
    bpy.app.handlers.depsgraph_update_post.append(selection_changed)


def unregister():
    bpy.utils.unregister_class(MRF_scene_config)
    del bpy.types.Scene.meta_reforge_config
    if selection_changed in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(selection_changed)
