import traceback
import bpy
from ..utils.blender.keep_state import EditorState
from ..classes.simple_joint import Joint
from ..utils.blender.unsorted import (
    duplicate_object,
    duplicate_mesh_light,
    join_objects,
    merge_by_distance,
    add_armature_modifier
)
from ..utils.blender.collection import (
    link_object_to_collection,
    collection_set_exclude
)
from ..globals import (
    INITIAL_SHAPE_COLLECTION,
    FINAL_SHAPE_COLLECTION,
    FBX_BODY_COLLECTION,
    FBX_HEAD_COLLECTION,
    SYSTEM_COLLECTION
)

def mesh_name(material_name: str) -> str:
    material_name = material_name.lower()
    if "headsynthesized" in material_name or "bodysynthesized" in material_name:
        return "skin"
    elif "teeth" in material_name:
        return "teeth"
    elif "lacrimal" in material_name:
        return "lacrimal"
    elif "eyerefractive_inst_l" in material_name:
        return "eye left"
    elif "eyerefractive_inst_r" in material_name:
        return "eye right"
    elif "eyeocclusion" in material_name:
        return "eye shell"
    elif "eyelash" in material_name:
        return "eyelashes"
    elif "cartilage" in material_name:
        return "cartilage"
    else:
        return "nan"
    

def clear_edit_objects(config) -> None:
    for item in config.edit_meshes:
        if item.basis_object is not None:
            bpy.data.objects.remove(item.basis_object, do_unlink=True)
        if item.final_object is not None:
            bpy.data.objects.remove(item.final_object, do_unlink=True)
    if config.edit_armature.basis_object:
        bpy.data.objects.remove(config.edit_armature.basis_object, do_unlink=True)
    if config.edit_armature.final_object:
        bpy.data.objects.remove(config.edit_armature.final_object, do_unlink=True)
    

def include_final_shape_only():
    collection_set_exclude(FBX_BODY_COLLECTION, True)
    collection_set_exclude(FBX_HEAD_COLLECTION, True)
    collection_set_exclude(INITIAL_SHAPE_COLLECTION, True)
    collection_set_exclude(SYSTEM_COLLECTION, True)
    collection_set_exclude(FINAL_SHAPE_COLLECTION, False)


def create_material_sets_by_slot(objects):
    """Creates sets of material names by slot index for a list of objects.

    Args:
        objects (list): A list of bpy.types.Object.

    Returns:
        list: A list of sets, each containing material names by their slot index.
    """
    material_sets = []

    for obj in objects:
        for i, mat_slot in enumerate(obj.material_slots):
            # Ensure the list has enough sets for all slots
            if len(material_sets) <= i:
                material_sets.append(set())

            if mat_slot.material:
                material_sets[i].add(mat_slot.material.name)

    return material_sets


def create_edit_meshes(
        context: bpy.types.Context,
        merge_distance: float,
        collection_name: str
) -> bpy.types.Object:

    config = context.scene.meta_reforge_config
    groups = {}
    if len(config.fbx_head_lods) != 0:
        lod_item = config.fbx_head_lods[0]
        for mesh_item in lod_item.mesh_items:
            group = groups.get(mesh_item.edit_id, None)
            if group is None:
                groups[mesh_item.edit_id] = group = list()
            group.append(mesh_item.final_object)
    if len(config.fbx_body_lods) != 0:
        lod_item = config.fbx_body_lods[0]
        for mesh_item in lod_item.mesh_items:
            group = groups.get(mesh_item.edit_id, None)
            if group is None:
                groups[mesh_item.edit_id] = group = list()
            group.append(mesh_item.final_object)

    edit_objects = list()
    for edit_id, group in groups.items():
        dups = []
        for obj in group:
            dups.append(
                duplicate_object(context, obj, collection_name=collection_name)
            )
        edit_object = join_objects(dups)
        merge_by_distance(edit_object, threshold=merge_distance, boundary_edges=True)
        edit_objects.append((edit_object, edit_id))

    return edit_objects


def create_light_lods(context: bpy.types.Context, collection_name: str) -> None:
    config = context.scene.meta_reforge_config

    for lod_item in config.fbx_head_lods:
        for mesh_item in lod_item.mesh_items:
            basis_object = duplicate_mesh_light(
                context,
                mesh_item.final_object,
                f"BASIS_{mesh_item.final_object.name}",
                collection_name
            )
            mesh_item.basis_object = basis_object

    for lod_item in config.fbx_body_lods:
        for mesh_item in lod_item.mesh_items:
            basis_object = duplicate_mesh_light(
                context,
                mesh_item.final_object,
                f"BASIS_{mesh_item.final_object.name}",
                collection_name
            )

            mesh_item.basis_object = basis_object


def create_edit_armature(context: bpy.types.Context) -> bpy.types.Object:
    config = context.scene.meta_reforge_config
    head_armature_obj = config.fbx_head_armature
    body_armature_obj = config.fbx_body_armature

    if head_armature_obj is not None:
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass
        bpy.context.view_layer.objects.active = head_armature_obj
        bpy.ops.object.mode_set(mode='EDIT')
        head_joints = Joint.from_edit_bones(head_armature_obj.data.edit_bones)
    else:
        head_joints = []

    if body_armature_obj is not None:
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.view_layer.objects.active = body_armature_obj
        bpy.ops.object.mode_set(mode='EDIT')
        body_joints = Joint.from_edit_bones(body_armature_obj.data.edit_bones)
    else:
        body_joints = []

    unique_joint_names = set()
    unique_joint_names.update([j.name for j in head_joints])
    unique_joint_names.update([j.name for j in body_joints])

    # Create a new armature object
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.armature_add()
    armature = bpy.context.active_object
    bpy.ops.object.mode_set(mode='EDIT')

    # Access the armature's edit bones
    edit_bones: bpy.types.ArmatureEditBones = armature.data.edit_bones

    # Remove automatically created bone
    for bone in edit_bones:
        edit_bones.remove(bone)
    
    for joint_name in unique_joint_names:
        # Create a new edit bone
        bone = edit_bones.new(joint_name)
        bone.length = 1.0

    # body_joints should be the last to be processed
    for joint in head_joints + body_joints:
        eb = edit_bones.get(joint.name)
        eb.matrix = joint.matrix
        if joint.parent is None:
            continue
        parent = edit_bones.get(joint.parent)
        eb.parent = parent if parent else None

    bpy.ops.object.mode_set(mode='OBJECT')
    return armature


class MRF_OT_init_objects(bpy.types.Operator):
    """
    Should be executed from the OBJECT mode
    """
    bl_idname = "meta_reforge.init_objects"
    bl_label = "Init Objects"
    bl_options = {'REGISTER', 'UNDO'}

    merge_distance: bpy.props.FloatProperty(name="Merge Distance", default=0.001, options={"HIDDEN"})
    keep_shape_keys: bpy.props.BoolProperty(name="Keep ShapeKeys", default=False, options={"HIDDEN"})
    tris_to_quads: bpy.props.BoolProperty(name="Tris To Quads", default=True, options={"HIDDEN"})

    @classmethod
    def poll(cls, context: bpy.types.Context):
        config = context.scene.meta_reforge_config
        return (
            config.max_num_lods != 0 and 
            (
                bool(config.fbx_head_armature) or
                bool(config.fbx_body_armature))
        )
    
    def execute(self, context):
        # Access config
        config = context.scene.meta_reforge_config
        state = EditorState.capture_current_state()
        try:
            print("Initializing edit objects")
            config.prepare_objects(context)

            # CLEAR
            clear_edit_objects(config)
            config.edit_meshes.clear()

            # FINAL ARMATURE
            final_armature = create_edit_armature(context)
            final_armature.name = "FINAL_ARMATURE"
            link_object_to_collection(final_armature, FINAL_SHAPE_COLLECTION, overwrite=True)
            config.edit_armature.final_object = final_armature

            # INITIAL ARMATURE
            initial_armature = duplicate_object(context, final_armature, "INITIAL_ARMATURE", INITIAL_SHAPE_COLLECTION)
            config.edit_armature.basis_object = initial_armature

            # Create init shape for each LOD
            create_light_lods(context, SYSTEM_COLLECTION)

            # Meshes
            edit_meshes = create_edit_meshes(
                context,
                merge_distance=self.merge_distance,
                collection_name=FINAL_SHAPE_COLLECTION
            )
            for final_mesh, edit_id in edit_meshes:
                final_mesh.name = f"{edit_id}_FINAL"

                with context.temp_override(obj=final_mesh):
                    bpy.ops.mesh.customdata_custom_splitnormals_clear()

                link_object_to_collection(final_mesh, FINAL_SHAPE_COLLECTION, overwrite=True)
                edit_mesh_item = config.edit_meshes.add()
                edit_mesh_item.final_object = final_mesh
                edit_mesh_item.edit_id = edit_id

                # Set up armature deform
                final_mesh.parent = final_armature
                final_mesh.modifiers.clear()
                add_armature_modifier(final_mesh, final_armature)

                # Initial mesh as the duplicate of the final mesh
                initial_mesh = duplicate_mesh_light(context, final_mesh, f"{edit_id}_INITIAL", INITIAL_SHAPE_COLLECTION)
                initial_mesh.modifiers.clear()
                # Triangulate initial meshes to avoid "concave" error
                context.view_layer.objects.active = initial_mesh
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_mode(type="FACE")
                bpy.ops.mesh.select_all(action="SELECT")
                bpy.ops.mesh.quads_convert_to_tris()
                bpy.ops.object.mode_set(mode='OBJECT')

                if not self.keep_shape_keys:
                    final_mesh.shape_key_clear()

                # Convert triangles to quads for editable (final) mesh
                if self.tris_to_quads:
                    context.view_layer.objects.active = final_mesh
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_mode(type="FACE")
                    bpy.ops.mesh.select_all(action="SELECT")
                    bpy.ops.mesh.tris_convert_to_quads()
                    bpy.ops.object.mode_set(mode='OBJECT')
                    edit_mesh_item.basis_object = initial_mesh

                # Set up armature deform
                initial_mesh.parent = initial_armature
                add_armature_modifier(initial_mesh, initial_armature)
            
            final_armature.select_set(True)
            for final_mesh, edit_id in edit_meshes:
                final_mesh.select_set(True)

            bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
            print("Initialization done")
            state.restore_state(active=final_mesh, selected=[final_mesh])
            include_final_shape_only()
        except Exception as ex:
            self.report({'ERROR'}, f"MRF_OT_init_objects operation failed: {str(ex)}")
            print(f"Operation failed: {str(ex)}")
            traceback.print_exc()
            state.try_restore()
            return {'CANCELLED'}
        return {'FINISHED'}


def register():
    bpy.utils.register_class(MRF_OT_init_objects)  


def unregister():
    bpy.utils.unregister_class(MRF_OT_init_objects)  


if __name__ == '__main__':
    register()
