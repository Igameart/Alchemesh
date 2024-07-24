import traceback
import bpy
import os
from typing import List, Tuple
from ..utils.blender.unsorted import (
    memorize_object_selection,
    restore_object_selection,
    memorize_mode,
    restore_mode,
    toggle_to_object_edit_mode,
    add_armature_modifier
)
from ..utils.blender.collection import (
    get_collection,
    link_objects_to_collection,
    collection_set_exclude
)
from ..utils.blender.fbx_io import import_fbx
from ..utils.blender.separate_by_material import separate_by_material
from ..utils.blender.unsorted import duplicate_mesh_light
from ..utils.common import print_progress_bar
from ..globals import (
    FBX_HEAD_COLLECTION,
    FBX_BODY_COLLECTION,
    FBX_CLOTH_COLLECTION,
    INITIAL_SHAPE_COLLECTION,
    DEFAULT_EDIT_ID,
    ADDON_DIRECTORY
)
from ..enums import BodyPart
from ..dna.dna_import import build_armature, build_meshes
from ..dna.io import get_reader


MESH_IDS = {
    "head",
    "teeth",
    "saliva",
    "eyeLeft",
    "eyeRight",
    "eyeshell",
    "eyelashes",
    "eyeEdge",
    "cartilage"
}


DNA_SHADER_EDIT_ID_MAP = {
    "shader_head_shader": "skin",
    "shader_teeth_shader": "teeth",
    "shader_saliva_shader": "saliva",
    "shader_eyeLeft_shader": "eyeLeft",
    "shader_eyeRight_shader": "eyeRight",
    "shader_eyeshell_shader": "eyeshell",
    "shader_eyelashes_shader": "eyelashes",
    "shader_eyeEdge_shader": "eyeEdge",
    "shader_cartilage_shader": "cartilage"
}

FBX_MATERIAL_INDEX_EDIT_ID_MAP = {
    0: {
        0: "skin",
        1: "teeth",
        2: "saliva",
        3: "eyeLeft",
        4: "eyeRight",
        5: "eyeshell",
        6: "eyelashes",
        7: "eyeEdge",
        8: "cartilage"
    },
    1: {
        0: "skin",
        1: "teeth",
        2: "saliva",
        3: "eyeLeft",
        4: "eyeRight",
        5: "eyeshell",
        6: "eyelashes",
        7: "eyeEdge",
        8: "cartilage"
    },
    2: {
        0: "skin",
        1: "teeth",
        2: "saliva",
        3: "eyeLeft",
        4: "eyeRight",
        5: "eyeshell",
        6: "eyelashes",
        7: "eyeEdge"
    },
    3: {
        0: "skin",
        1: "teeth",
        2: "eyeLeft",
        3: "eyeRight",
        4: "eyeshell",
        5: "eyelashes",
        6: "eyeEdge"
    },
    4: {
        0: "skin",
        1: "teeth",
        2: "eyeLeft",
        3: "eyeRight",
        4: "eyeshell"
    },
    5: {
        0: "skin",
        1: "teeth",
        2: "eyeLeft",
        3: "eyeRight"
    },
    6: {
        0: "skin",
        1: "teeth",
        2: "eyeLeft",
        3: "eyeRight"
    },
    7: {
        0: "skin",
        1: "teeth",
        2: "eyeLeft",
        3: "eyeRight"
    }
}

HEAD_EDIT_ID2MAT_MAP = {
    "default": {"name": "default", "rgba": (0.3, 0.3, 0.3, 1.0), "roughness": 0.5, "metallic": 0.0},
    "skin": {"name": "shader_head_shader", "rgba": (0.3, 0.3, 0.3, 1.0), "roughness": 0.5, "metallic": 0.0},
    "teeth": {"name": "shader_teeth_shader", "rgba": (0.3, 0.3, 0.3, 1.0), "roughness": 0.1, "metallic": 0.0},
    "saliva": {"name": "shader_saliva_shader", "rgba": (0.3, 0.3, 0.3, 0.5), "roughness": 0.1, "metallic": 0.0},
    "eyeLeft": {
        "name": "shader_eyeLeft_shader",
        "rgba": (1.0, 1.0, 1.0, 1.0),
        "roughness": 0.1,
        "metallic": 0.0,
        "texture": os.path.join(ADDON_DIRECTORY, "textures", "eye_simple.png")
    },
    "eyeRight": {
        "name": "shader_eyeRight_shader",
        "rgba": (1.0, 1.0, 1.0, 1.0),
        "roughness": 0.1,
        "metallic": 0.0,
        "texture": os.path.join(ADDON_DIRECTORY, "textures", "eye_simple.png")
    },
    "eyeshell": {"name": "shader_eyeshell_shader", "rgba": (0.3, 0.3, 0.3, 0.1), "roughness": 0.1, "metallic": 0.0},
    "eyelashes": {"name": "shader_eyelashes_shader", "rgba": (0.3, 0.3, 0.3, 1.0), "roughness": 0.7, "metallic": 0.0},
    "eyeEdge": {"name": "shader_eyeEdge_shader", "rgba": (0.3, 0.3, 0.3, 0.5), "roughness": 0.1, "metallic": 0.0},
    "cartilage": {"name": "shader_cartilage_shader", "rgba": (0.3, 0.3, 0.3, 0.5), "roughness": 0.3, "metallic": 0.0}
}

BODY_EDIT_ID2MAT_MAP = {
    "default": {"name": "default", "rgba": (0.3, 0.3, 0.3, 1.0), "roughness": 0.5, "metallic": 0.0},
    "skin": {"name": "M_BodySynthesized", "rgba": (0.3, 0.3, 0.3, 1.0), "roughness": 0.5, "metallic": 0.0}
}

def set_material_texture(material: bpy.types.Material, image_path: str) -> None:
    material.use_nodes = True
    nodes = material.node_tree.nodes

    # Clear all nodes to start fresh
    for node in nodes:
        nodes.remove(node)

    # Create an Image Texture node
    texture_node = nodes.new(type='ShaderNodeTexImage')
    texture_node.location = (0,0)

    # Load the image
    image = bpy.data.images.load(image_path)
    texture_node.image = image

    # Create a BSDF shader
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (200,0)

    # Link Image Texture node to BSDF
    material.node_tree.links.new(bsdf.inputs['Base Color'], texture_node.outputs['Color'])

    # Create Material Output node
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (400,0)

    # Link BSDF to Material Output
    material.node_tree.links.new(output_node.inputs['Surface'], bsdf.outputs['BSDF'])

def remove_unwanted_shape_keys(obj, shape_keys_to_remove: list):
    """
    Removes shape keys from the given object that do not start with edit_id
    but start with any of the prefixes in prefixes list.
    """
    
    if not obj.data.shape_keys:
        return
    
    old_active = bpy.context.view_layer.objects.active
    bpy.context.view_layer.objects.active = obj
    key_blocks = obj.data.shape_keys.key_blocks

    if len(key_blocks) == len(shape_keys_to_remove) + 1:
        purge_all = True
        for kb in key_blocks[1:]:
            if kb.name not in shape_keys_to_remove:
                purge_all = False
                break
        if purge_all:
            bpy.ops.object.shape_key_remove(all=True)
            return
    for key_name in shape_keys_to_remove:
        kb = key_blocks.get(key_name)
        if kb:
            obj.shape_key_remove(kb)
    bpy.context.view_layer.objects.active = old_active


def mrf_load_objects_from_fbx(
        context: bpy.types.Context,
        body_part: BodyPart,
        remove_remaining: bool = True
    ):
    """
    Load initial object from FBX
    """
    config = context.scene.meta_reforge_config
    
    if body_part == BodyPart.HEAD:
        id2mat = HEAD_EDIT_ID2MAT_MAP
        collection = config.fbx_head_lods
        path = config.fbx_head_path
    else:
        id2mat = BODY_EDIT_ID2MAT_MAP
        collection = config.fbx_body_lods
        path = config.fbx_body_path
    
    # Import objects from FBX
    path = bpy.path.abspath(path)
    objects = import_fbx(context, path)
    # Sort the names of the objects
    objects = sorted(objects, key=lambda x: x.name)
    armature = None
    
    meshes = []
    lod_index = 0
    for obj in objects:
        if obj.type == "ARMATURE":
            if armature is None:
                armature = obj
            else:
                raise Exception("The list of objects should contain only one armature object")
        elif obj.type == "MESH":
            materials = [mat.name if mat else "NONE" for mat in obj.data.materials]
            while len(collection) < lod_index + 1:
                collection.add()
            lod_item = collection[lod_index]
            lod_group = separate_by_material(obj)
            for lod_part in lod_group:
                mesh_item = lod_item.mesh_items.add()
                mesh_item.final_object = lod_part
                material_name = lod_part.data.materials[0].name
                material_index = materials.index(material_name)
                edit_id = FBX_MATERIAL_INDEX_EDIT_ID_MAP.get(lod_index, dict()).get(material_index, "default")
                mesh_item.edit_id = edit_id
                if body_part is BodyPart.HEAD:
                    lod_part.name = f"{edit_id}_lod{lod_index}"
                else:
                    lod_part.name = f"body_{edit_id}_lod{lod_index}"
                
                mesh_id = "head" if edit_id == "skin" else edit_id
                lod_id = f"lod{lod_index}"
                if lod_part.data.shape_keys:
                    redundant_sk = []
                    key_blocks = lod_part.data.shape_keys.key_blocks
                    for k in key_blocks[1:]:
                        if lod_id not in k.name:
                            redundant_sk.append(k.name)
                            continue
                        if k.name.startswith(mesh_id):
                            continue
                        if any([k.name.startswith(pfx) for pfx in MESH_IDS]):
                            redundant_sk.append(k.name)

                    remove_unwanted_shape_keys(lod_part, redundant_sk)

                material_data = id2mat.get(edit_id, None)
                if material_data:
                    mat = bpy.data.materials.get(material_data["name"], None)
                    if mat is None:
                        mat = bpy.data.materials.new(material_data["name"])
                    if mat.diffuse_color != material_data["rgba"]:
                        mat.diffuse_color = material_data["rgba"]
                        mat.roughness = material_data["roughness"]
                        mat.metallic = material_data["metallic"]
                        mat.use_nodes = True
                        texture_path = material_data.get("texture", None)
                        if texture_path:
                            set_material_texture(mat, image_path=texture_path)
                    lod_part.data.materials[0] = mat
                meshes.append(lod_part)
            lod_index += 1
        elif remove_remaining:
            bpy.data.objects.remove(obj)
    
    if armature is None:
        raise Exception("The list of objects should contain armature")
    if len(meshes) == 0:
        raise Exception("The list of objects at least one LOD")

    if body_part == BodyPart.BODY:
        config.fbx_body_armature = armature
    elif body_part == BodyPart.HEAD:
        config.fbx_head_armature = armature

    if config.fbx_head_override_bone_length:
        override_bone_length(armature, new_length=config.fbx_head_bone_length)
    
    # Link to necessary collection
    if body_part == BodyPart.HEAD:
        link_objects_to_collection(meshes + [armature], FBX_HEAD_COLLECTION, override=True)
    else:
        link_objects_to_collection(meshes + [armature], FBX_BODY_COLLECTION, override=True)
    
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    return armature, meshes


def mrf_load_cloth_from_fbx(
        context: bpy.types.Context,
        remove_remaining: bool = True
    ):
    """
    Load initial object from FBX
    """
    config = context.scene.meta_reforge_config
    # Import objects from FBX
    path = bpy.path.abspath(config.cloth_import_path)
    objects = import_fbx(context, path)
    # Sort the names of the objects
    objects = sorted(objects, key=lambda x: x.name)
    armature = None

    cloth_item = config.cloth_items.add()
    collection = cloth_item.lod_items
    meshes = []
    lod_index = 0
    for obj in objects:
        if obj.type == "ARMATURE":
            if armature is None:
                armature = obj
            else:
                raise Exception("The list of objects should contain only one armature object")
        elif obj.type == "MESH":
            while len(collection) < lod_index + 1:
                collection.add()
            lod_item = collection[lod_index]
            lod_item.final_object = obj
            lod_item.basis_object = duplicate_mesh_light(context, obj, f"{obj.name}_BASIS", INITIAL_SHAPE_COLLECTION)
            lod_item.edit_id = DEFAULT_EDIT_ID
            meshes.append(obj)
            lod_index += 1
        elif remove_remaining:
            bpy.data.objects.remove(obj)
    
    if armature is None:
        raise Exception("The list of objects should contain armature")
    if len(meshes) == 0:
        raise Exception("The list of objects at least one LOD")

    basename = os.path.basename(path)
    cloth_item.item_name = os.path.splitext(basename)[0]
    cloth_item.armature = armature

    if config.fbx_head_override_bone_length:
        override_bone_length(armature, new_length=config.fbx_head_bone_length)
    
    # Link to necessary collection
    collection_set_exclude(INITIAL_SHAPE_COLLECTION, exclude=True)

    parent_collection = get_collection(FBX_CLOTH_COLLECTION, ensure_exist=True)
    collection = bpy.data.collections.new(basename)
    parent_collection.children.link(collection)
    for obj in meshes + [armature]:
        for coll in obj.users_collection:
            if coll != collection:
                coll.objects.unlink(obj)
        collection.objects.link(obj)
    
    return armature, meshes


def mrf_build_head_from_dna(context: bpy.types.Context) -> None:
    config = context.scene.meta_reforge_config
    dna_path = config.absolute_dna_path
    reader = get_reader(dna_path)
    armature = build_armature(reader, apply_transforms=True, complete_skeleton=True)
    config.fbx_head_armature = armature
    basename = os.path.basename(dna_path)
    config.export_name = os.path.splitext(basename)[0]
    lods = build_meshes(reader, apply_transforms=True, shape_key_threshold=config.build_head_morph_threshold)
    meshes = []
    
    collection = config.fbx_head_lods
    collection.clear()
    for _, mesh_objects in lods.items():
        lod_item = collection.add()
        meshes += mesh_objects
        for lod_part in mesh_objects:
            mesh_item = lod_item.mesh_items.add()
            mesh_item.final_object = lod_part
            mat = lod_part.data.materials[0]
            for k, v in DNA_SHADER_EDIT_ID_MAP.items():
                if k not in mat.name:
                    continue
                mesh_item.edit_id = v
                material_data = HEAD_EDIT_ID2MAT_MAP.get(v, None)

                if material_data:
                    if mat.name != material_data["name"]:
                        mat = bpy.data.materials.get(material_data["name"], None)
                        if mat is None:
                            mat = bpy.data.materials.new(material_data["name"])
                    mat.diffuse_color = material_data["rgba"]
                    mat.roughness = material_data["roughness"]
                    mat.metallic = material_data["metallic"]
                    mat.use_nodes = True
                    texture_path = material_data.get("texture", None)
                    if texture_path:
                        set_material_texture(mat, image_path=texture_path)
                break  
    for mesh in meshes:
        add_armature_modifier(mesh, armature)
        mesh.parent = armature
    link_objects_to_collection(meshes + [armature], FBX_HEAD_COLLECTION, override=True)


def execute_import(context: bpy.types.Context) -> None:
    config = context.scene.meta_reforge_config
    if config.import_head:
        if config.build_head_from_dna:
            mrf_build_head_from_dna(context)
        else:
            mrf_load_objects_from_fbx(context, body_part=BodyPart.HEAD, remove_remaining=True)
    if config.import_body:
        mrf_load_objects_from_fbx(context, body_part=BodyPart.BODY, remove_remaining=True)
    return {'FINISHED'}


def filepath_is_valid(path: str, extention: str) -> bool:
    # Check if the file exists
    if not os.path.exists(path):
        return False
    _, ext = os.path.splitext(path)
    if ext.lower() != extention.lower():
        return False
    return True
    

def check_for_import(context: bpy.types.Context) -> Tuple[bool, str]:
    config = context.scene.meta_reforge_config
    if config.import_head:
        if config.build_head_from_dna:
            path = bpy.path.abspath(config.dna_path)
            if not filepath_is_valid(path, ".dna"):
                return False, "Invalid DNA path"
        else:
            path = bpy.path.abspath(config.fbx_head_path)
            if not filepath_is_valid(path, ".fbx"):
                return False, "Invalid head FBX path"
    if config.import_body:
        path = bpy.path.abspath(config.fbx_body_path)
        if not filepath_is_valid(path, ".fbx"):
            return False, "Invalid body FBX path"
    return True, "Ok"


def check_for_import_cloth(context: bpy.types.Context) -> Tuple[bool, str]:
    config = context.scene.meta_reforge_config
    path = bpy.path.abspath(config.cloth_import_path)
    if filepath_is_valid(path, ".fbx"):
        return True, "Ok"
    else:
        return False, "Invalid Cloth FBX Path"


def check_for_dna_export(context: bpy.types.Context) -> Tuple[bool, str]:
    config = context.scene.meta_reforge_config
    path = bpy.path.abspath(config.dna_path)
    if filepath_is_valid(path, ".dna"):
        return True, "Ok"
    else:
        return False, "Invalid DNA Path"


def override_bone_length(armature: bpy.types.Object, new_length: float) -> None:
    memorize_object_selection()
    memorize_mode()

    toggle_to_object_edit_mode(bpy.context, armature)
    armature_data: bpy.types.Armature = armature.data
    for bone in armature_data.edit_bones:
        bone.length = new_length
    restore_mode()
    restore_object_selection()


class MRF_OT_import(bpy.types.Operator):
    bl_idname = "meta_reforge.import"
    bl_label = "Import"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Import metahuman head and body. It is recommended to import both"
     
    def execute(self, context):
        try:
            execute_import(context)
            return {'FINISHED'}
        except Exception as ex:
            msg = f"Import failed: {str(ex)}"
            print("ERROR: {msg}")
            print(traceback.format_exc())
            self.report({"ERROR"}, msg)
            return {'CANCELLED'}
        

class MRF_OT_import_cloth(bpy.types.Operator):
    bl_idname = "meta_reforge.import_cloth"
    bl_label = "Import Cloth"
    bl_options = {'REGISTER', 'UNDO'}
     
    def execute(self, context):
        try:
            mrf_load_cloth_from_fbx(context, remove_remaining=True)
            return {'FINISHED'}
        except Exception as ex:
            msg = f"Cloth import failed: {str(ex)}"
            print("ERROR: {msg}")
            print(traceback.format_exc())
            self.report({"ERROR"}, msg)
            return {'CANCELLED'}


classes = [MRF_OT_import, MRF_OT_import_cloth]  

def register():
    for cl in classes:
        bpy.utils.register_class(cl)  


def unregister():
    for cl in classes:
        bpy.utils.unregister_class(cl)


if __name__ == '__main__':
    register()
