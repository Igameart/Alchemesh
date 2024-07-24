import bpy
import time
import random
from ..utils.blender.unsorted import (
    restore_object_selection,
    memorize_object_selection,
    toggle_to_objects_edit_mode
)
from ..utils.blender.collection import (
    collection_set_exclude,
    collection_get_exclude
)

from ..utils.blender.visibility import (
    memorize_objects_visibility,
    restore_objects_visibility,
    reveal_collection
)
from ..globals import (
    INITIAL_SHAPE_COLLECTION,
)
from ..classes.octa import Octa
from ..classes.barrycentric_triangle import BarrycentricTriangle


def fit_bones_check_type(
        initial_armature_object: bpy.types.Object,
        initial_mesh_object: bpy.types.Object,
        final_armature_object: bpy.types.Object,
        final_mesh_object: bpy.types.Object,
        ) -> None:
    if initial_mesh_object.type != "MESH":
        raise TypeError("Type of initial_mesh_object should be \"MESH\"")
    if final_mesh_object.type != "MESH":
        raise TypeError("Type of final_mesh_object should be \"MESH\"")
    if initial_armature_object.type != "ARMATURE":
        raise TypeError("Type of initial_armature_object should be \"ARMATURE\"")
    if final_armature_object.type != "ARMATURE":
        raise TypeError("Type of final_armature_object should be \"ARMATURE\"")
    

def get_py_vg_data(mesh_object: bpy.types.Object) -> dict:
    vertex_groups = mesh_object.vertex_groups
    vg_data = {vg.index: dict() for vg in vertex_groups}
    
    # Filter weights by threshold
    threshold = 0.01
    for vertex in mesh_object.data.vertices:
        for vg in vertex.groups:
            if vg.weight >= threshold:
                vg_group_data = vg_data[vg.group]
                vg_group_data[vertex.index] = vg.weight

    # Rename keys
    vg_rename_map = {vg.index: vg.name for vg in vertex_groups}
    vg_data = {vg_rename_map.get(key, key): value for key, value in vg_data.items()}
    return vg_data



def fit_bones_wrt(
        context: bpy.types.Context,
        initial_armature_object: bpy.types.Object,
        initial_mesh_object: bpy.types.Object,
        final_armature_object: bpy.types.Object,
        final_mesh_object: bpy.types.Object,
        iterations: int = 100
        ) -> None:
    t1 = time.time()
    
    fit_bones_check_type(
        initial_armature_object,
        initial_mesh_object,
        final_armature_object,
        final_mesh_object
        )
    initial_mesh: bpy.types.Mesh = initial_mesh_object.data
    deformed_mesh: bpy.types.Mesh = final_mesh_object.data
    if len(initial_mesh.vertices) != len(deformed_mesh.vertices):
        raise IndexError("Initial and deformed mesh should be of the same number of vertices")
    
    if len(initial_mesh.polygons) != len(deformed_mesh.polygons):
        raise IndexError("Initial and deformed mesh should be of the same number of vertices")
    
    toggle_to_objects_edit_mode(context, [initial_armature_object, final_armature_object])
    
    vg_data = get_py_vg_data(initial_mesh_object)

    deformed_bones = final_armature_object.data.edit_bones
    initial_bones = initial_armature_object.data.edit_bones
    
    for vg_name, vg_group_data in vg_data.items():
        if len(vg_group_data) < 3:
            continue
        if vg_name not in initial_bones or vg_name not in deformed_bones:
            continue
        initial_bone: bpy.types.EditBone = initial_bones[vg_name]
        deformed_bone: bpy.types.EditBone = deformed_bones[vg_name]
        if not deformed_bone.select:
            continue
        structure = Octa.from_bone(initial_bone, offset=0.01)
        structures = []
        weights = []
        vertex_indices = list(vg_group_data.keys())
        for i in range(iterations):
            tri_indices = random.sample(vertex_indices, 3)
            tri_weights = [vg_group_data[index] for index in tri_indices]
            tri_old = [initial_mesh.vertices[index].co for index in tri_indices]
            tri_new = [deformed_mesh.vertices[index].co for index in tri_indices]
            
            triangle = BarrycentricTriangle(tri_old, tri_new)
            
            if not triangle.valid:
                continue

            weight = sum(tri_weights) / 3.0
            
            weight += triangle.calc_triangle_weight()

            structures.append(triangle.deform_structure(structure))
            weights.append(weight)
    
        new_octa = Octa.average(structures, weights)
        matrix = new_octa.to_matrix()
        deformed_bone.matrix = matrix
    print(f"Time elapsed: {time.time() - t1}")


class MRF_OT_fit_bones_with_wrt(bpy.types.Operator):
    bl_idname = "meta_reforge.fit_bones_wrt"
    bl_label = "Fit Bones with Weighted Random Triangles"
    bl_description = "Fit bones with custom algorythom that utilizes weighted (bone weight) random triangles"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        config = context.scene.meta_reforge_config
        return (
            bool(config.initial_edit_armature) 
            and bool(config.initial_edit_mesh)
            and bool(config.final_edit_armature)
            and bool(config.final_edit_mesh)
        )
    
    def execute(self, context):
        """
        RUNS FROM ARMATURE EDIT MODE
        """
        initial_source_collection_exclude_state = collection_get_exclude(INITIAL_SHAPE_COLLECTION)
        memorize_object_selection()
        memorize_objects_visibility()
        reveal_collection(INITIAL_SHAPE_COLLECTION)
        
        config = context.scene.meta_reforge_config
        fit_bones_wrt(
            context,
            initial_armature_object=config.initial_edit_armature,
            initial_mesh_object=config.initial_edit_mesh,
            final_armature_object=config.final_edit_armature,
            final_mesh_object=config.final_edit_mesh
        )
        bpy.ops.object.mode_set(mode="OBJECT")
        restore_objects_visibility()
        restore_object_selection()
        collection_set_exclude(INITIAL_SHAPE_COLLECTION, exclude=initial_source_collection_exclude_state)
        bpy.ops.object.mode_set(mode="EDIT")
        return {'FINISHED'}
    

classes = [MRF_OT_fit_bones_with_wrt]
    

def register():
    for c in classes:
        bpy.utils.register_class(c)   


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)  


if __name__ == '__main__':
    register()
