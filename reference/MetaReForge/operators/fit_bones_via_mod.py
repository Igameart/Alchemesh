import traceback
import bpy
from typing import List

from ..utils.blender.unsorted import (
    create_empty_mesh_object,
    get_deformed_vertices,
    toggle_to_object_edit_mode,
    add_surface_deform_modifier,
    add_mesh_deform_modifier
)
from ..utils.blender.shape_keys import join_as_shape
from ..utils.blender.object import ensure_objects_visible
from ..utils.blender.keep_state import EditorState
from ..utils.blender.armature import transfer_rest_pose
from ..classes.octa import Octa


# def kdtree_from_bones(edit_bones: Union[bpy.types.bpy_prop_collection, List[bpy.types.EditBone]]) -> KDTree:
#     """
#     Constructs and balances a KDTree from the head positions of a collection of edit bones.

#     :param edit_bones: Collection or list of edit bones from which the KDTree will be created.
#     :returns: balanced KDTree with each node corresponding to the head position of an edit bone.
#     """
#     kd = KDTree(size=len(edit_bones))
#     for index, bone in enumerate(edit_bones):
#         kd.insert(bone.head, index)
#     kd.balance()
#     return kd


# def octa_offsets_from_bone(bone: bpy.types.EditBone, offset: float) -> List[Vector]:
#     """
#     Computes offsets along the bone's local axes. When these offsets are added to
#     the bone's head position, it will form an octahedral structure centered around the bone's head.

#     :param bone: The bone object from which the offsets will be derived.
#     :param offset: The distance from the bone's head in each direction.

#     :returns: list of offsets along the bone's local axes (X, -X, Y, -Y, Z, -Z) in object coordinates
#     """
#     offsets_bone_local = [
#         (offset, 0.0, 0.0),   # positive X
#         (-offset, 0.0, 0.0),  # negative X
#         (0.0, offset, 0.0),   # positive Y   
#         (0.0, -offset, 0.0),  # negative Y
#         (0.0, 0.0, offset),   # positive Z
#         (0.0, 0.0, -offset)   # negative Z
#     ]
#     return [bone.matrix.to_3x3() @ Vector(offset) for offset in offsets_bone_local]


# def find_shortest_nonzero_distance(kd: KDTree, co: Vector, tolerance: float = 1e-4):
#     """
#     Finds the shortest nonzero distance from a given point to the nearest points in a KDTree.

#     :param kd: KDTree containing the points for searching.
#     :param co: Vector representing the point from which the distance is measured.
#     :param tolerance: Minimum allowable distance. Distances below this are considered too close.

#     :returns: Shortest nonzero distance from the given point to the KDTree's points, or None if all
#               distances are below the tolerance.
#     """
#     for _, _, dist in kd.find_n(co, 2):
#         if dist >= tolerance:
#             return dist
#     # If the distances of the two nearest points are below the tolerance,
#     # then search further within the KDTree to find an appropriate distance
#     for _, _, dist in kd.find_n(co, 9999):
#         if dist >= tolerance:
#             return dist
#     return


def init_proxy_deform_mesh(
        context: bpy.types.Context,
        armature_object: bpy.types.Object,
        name: str,
        bone_names: list = None,
        octa_offset: float = 0.01
) -> bpy.types.Object:
    """
    Initializes a proxy deform mesh based on an armature's structure.

    This function creates a proxy mesh object which mimics the structure of an armature
    by generating vertices and edges that correspond to the armature's bones. Each bone gets
    a set of vertices around its head, forming an octahedral pattern. These vertices are 
    then assigned to corresponding vertex groups named after the bones.

    :param context: The current Blender context.
    :param armature_object: The armature object based on which the proxy mesh will be generated.

    :returns: The newly created proxy mesh object.

    :raises Exception: If the provided object is not a valid armature.
    """

    if not armature_object or armature_object.type != 'ARMATURE':
        raise Exception("No armature selected")

    # Set the armature as the active object in object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    armature_object.select_set(True)
    context.view_layer.objects.active = armature_object

    # Switch to edit mode for the armature
    bpy.ops.object.mode_set(mode='POSE')

    # Create the proxy mesh object
    proxy = bpy.data.objects.get(name)
    if proxy:
        bpy.data.objects.remove(proxy, do_unlink=True)
    proxy = create_empty_mesh_object(name)

    # [ADJ] Generate a KDTree based on the armature's bones
    # kd = kdtree_from_bones(armature.edit_bones)

    vertices, edges, faces = [], [], []
    # [ADJ] min_offset, max_offset, offset_factor = 0.01, 0.1, 0.01
    bone_vertex_dict = {}

    matrix = armature_object.matrix_world
    # Iterate over each bone to create vertices and edges for the proxy mesh
    for bone in armature_object.pose.bones: # armature.edit_bones
        if bone_names and bone.name not in bone_names:
            continue
        # Add the bone's head position as a central vertex
        v_central_idx = len(vertices)
        vertices.append(matrix @ bone.head.copy())
        
        # [ADJ] Calculate and add offset vertices around the bone's head
        # closest_dist = find_shortest_nonzero_distance(kd, bone.head)
        # octa_offset = limit(closest_dist * offset_factor, min_offset, max_offset)
        bone_vertices = [v_central_idx]
        octa = Octa.from_bone(bone, octa_offset)
        for vertex in octa.vertices:
            vertices.append(matrix @ vertex)
            new_vertex_idx = len(vertices) - 1
            edges.append([v_central_idx, new_vertex_idx])
            bone_vertices.append(new_vertex_idx)

        bone_vertex_dict[bone.name] = bone_vertices

    # Define the geometry for the proxy mesh
    proxy.data.from_pydata(vertices, edges, faces)
    proxy.data.update()

    # Assign vertices to vertex groups named after the armature's bones
    for bone_name, indices in bone_vertex_dict.items():
        vg = proxy.vertex_groups.new(name=bone_name)
        vg.add(indices, 1.0, 'ADD')

    # Return to object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    return proxy


def transfer_deform_from_proxy(
        context: bpy.types.Context,
        armature_object: bpy.types.Object,
        proxy_object: bpy.types.Object,
        bone_names: List[str] = None,
        lock_rotation: bool = False
    ) -> None:
    """
    Transfers deformations from a proxy mesh object to an armature.

    This function uses the deformations and vertex groups of a proxy mesh to 
    adjust the transformations of the bones in the corresponding armature. Each 
    vertex group in the proxy mesh corresponds to a bone in the armature. The 
    function recalculates the bone's matrix based on the deformed positions of 
    the vertices in its corresponding vertex group.

    :param context: The current Blender context.
    :param armature_object: The armature object that will be modified.
    :param proxy_object: The proxy mesh object containing the deformations and vertex groups.
    :param lock_rotation: Locks initial bone rotation
    
    :returns: None
    """

    # Set the armature as the active object in object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    armature_object.select_set(True)
    context.view_layer.objects.active = armature_object
    armature = armature_object.data

    # Switch to edit mode for the armature
    bpy.ops.object.mode_set(mode='EDIT')

    # Initialize a dictionary to store vertex coordinates per vertex group
    bone_vertex_dict = {vg.index: list() for vg in proxy_object.vertex_groups}
    
    # Retrieve the deformed vertices from the proxy object
    deformed_vertices = get_deformed_vertices(context, proxy_object)
    
    # Populate the bone_vertex_dict with the deformed vertex coordinates
    for vertex in deformed_vertices:
        for group in vertex.groups:
            if group.weight > 0:
                bone_vertex_dict[group.group].append(vertex.co)

    # Convert vertex group indices back to bone names
    bone_vertex_dict = {proxy_object.vertex_groups[key].name: value for key, value in bone_vertex_dict.items()}

    # Iterate over each bone to adjust its transformation matrix
    for bone_name, vertices in bone_vertex_dict.items():
        if bone_names is not None and bone_name not in bone_names:
            continue
        bone = armature.edit_bones[bone_name]
        if lock_rotation:
            bone_vec = bone.tail - bone.head
            bone.head = vertices[0]
            bone.tail = bone.head + bone_vec
        else:
            octa = Octa(center=vertices[0], vertices=vertices[1:])
            bone.matrix = octa.to_matrix()

    # Return to Object Mode
    bpy.ops.object.mode_set(mode='OBJECT')


class MRF_OT_init_surface_deform_proxy(bpy.types.Operator):
    bl_idname = "meta_reforge.init_surface_deform_proxy"
    bl_label = "Init Surface Deform Proxy"
    bl_description = "Initialize surface deformation proxy"
    bl_options = {'REGISTER', 'UNDO'}

    falloff: bpy.props.FloatProperty(
        name="Falloff",
        description="Surface Deform Fallof",
        min=2, max=16, default=4,
        options={"HIDDEN"}
        )
    proxy_name: bpy.props.StringProperty("Proxy Name", default="SD_PROXY", options={"HIDDEN"})
    basis_mesh_name: bpy.props.StringProperty("Target Mesh Name")
    basis_armature_name: bpy.props.StringProperty("Basis Armature Name")

    def execute(self, context):
        state = EditorState.capture_current_state()
        try:
            print("Initializing Surface Deform proxy object")
            deform_target = bpy.data.objects.get(self.basis_mesh_name, None)
            if deform_target is None:
                raise KeyError(f"Fit bones target object ({self.basis_mesh_name}) is not found")

            basis_armature = bpy.data.objects.get(self.basis_armature_name, None)
            if basis_armature is None:
                raise KeyError(f"Fit bones basis armature ({self.basis_armature_name}) is not found")

            ensure_objects_visible([deform_target, basis_armature])
            # Generate proxy from initial armature
            bone_names = [b.name for b in context.active_object.data.edit_bones if b.select]
            proxy = init_proxy_deform_mesh(context, basis_armature, name=self.proxy_name, bone_names=bone_names)
            # Bind proxy to joined basis (initial) mesh
            deformer = add_surface_deform_modifier(
                context,
                proxy,
                "PROXY_SURFACE_DEFORM",
                deform_target,
                self.falloff,
                ovewrite_if_exists=True
            )
            context.view_layer.update()
            
            if not deformer.is_bound:
                raise Exception("Unable to bind Surface Deform Modifier")
            
            proxy.hide_set(True)
            deform_target.hide_set(True)
            print("Initialization done")
            return {'FINISHED'}
        except Exception as ex:
            self.report({'ERROR'}, f"MRF_OT_init_surface_deform_proxy operation failed: {str(ex)}")
            print(traceback.format_exc())
            return {'CANCELLED'}
        finally:
            state.restore_state()


class MRF_OT_init_mesh_deform_proxy(bpy.types.Operator):
    bl_idname = "meta_reforge.init_mesh_deform_proxy"
    bl_label = "Init Mesh Deform Proxy"
    bl_description = "Initialize Mesh Deformation proxy"
    bl_options = {'REGISTER', 'UNDO'}

    precision: bpy.props.IntProperty(
        name="Precision",
        description="The grid size for binding",
        min=2, max=10, default=4,
        options={"HIDDEN"}
        )
    proxy_name: bpy.props.StringProperty("Proxy Name", default="MD_PROXY", options={"HIDDEN"})
    basis_mesh_name: bpy.props.StringProperty("Target Mesh Name")
    basis_armature_name: bpy.props.StringProperty("Basis Armature Name")

    
    def execute(self, context):
        state = EditorState.capture_current_state()
        try:
            print("Initializing Mesh Deform proxy object")
            deform_target = bpy.data.objects.get(self.basis_mesh_name, None)
            if deform_target is None:
                raise KeyError(f"Fit bones target object ({self.basis_mesh_name}) is not found")

            basis_armature = bpy.data.objects.get(self.basis_armature_name, None)
            if basis_armature is None:
                raise KeyError(f"Fit bones basis armature ({self.basis_armature_name}) is not found")
            ensure_objects_visible([basis_armature, deform_target])
            # Generate proxy from initial armature
            bone_names = [b.name for b in context.active_object.data.edit_bones if b.select]
            proxy = init_proxy_deform_mesh(context, basis_armature, name=self.proxy_name, bone_names=bone_names)
            # Bind proxy to initial mesh
            deformer = add_mesh_deform_modifier(
                context,
                proxy,
                "PROXY_MESH_DEFORM",
                deform_target,
                precision=self.precision,
                ovewrite_if_exists=True
            )
            
            context.view_layer.update()

            if not deformer.is_bound:
                raise Exception("Unable to bind Mesh Deform Modifier")
            
            proxy.hide_set(True)
            deform_target.hide_set(True)
            print("Initialization done")
            return {'FINISHED'}
        except Exception as ex:
            self.report({'ERROR'}, f"MRF_OT_init_surface_deform_proxy operation failed: {str(ex)}")
            print(traceback.format_exc())
            return {'CANCELLED'}
        finally:
            state.restore_state()

        
def fit_bones(
        context: bpy.types.Context,
        armature_object: bpy.types.Object,
        proxy: bpy.types.Object,
        final_object: bpy.types.Object,
        basis_object: bpy.types.Object,
        bone_names: List[str],
        lock_rotation: bool
) -> None:    
    # Get list of the bones to process
    toggle_to_object_edit_mode(context, armature_object)

    final_sk = join_as_shape(basis_object, final_object, shape_key_name="FINAL_SHAPE", replace=True) 

    final_sk.value = 1.0
    basis_object.data.update()

    # Transfer deformation
    transfer_deform_from_proxy(context, armature_object, proxy, bone_names, lock_rotation)
    
    final_sk.value = 0.0
    basis_object.shape_key_remove(final_sk)
      

class MRF_OT_fit_bones(bpy.types.Operator):
    bl_idname = "meta_reforge.fit_bones"
    bl_label = "Fit Bones"
    bl_description = "Fit Bones with Surface or Mesh Deform modifier"
    bl_options = {'REGISTER', 'UNDO'}

    proxy_name: bpy.props.StringProperty(name="Proxy Object Name", default="SD_PROXY", options={"HIDDEN"})
    basis_mesh_name: bpy.props.StringProperty(name="Target Mesh Name", options={"HIDDEN"})
    final_mesh_name: bpy.props.StringProperty(name="Final Target Mesh Name", options={"HIDDEN"})
    basis_armature_name: bpy.props.StringProperty(name="Basis Armature Name", options={"HIDDEN"})
    lock_rotation: bpy.props.BoolProperty(name="Lock Rotation", default=True, options={"HIDDEN"})


    def execute(self, context):
        print(f"Fitting bones with {self.proxy_name} proxy object")
        state = EditorState.capture_current_state()
        try:
            # Check proxy
            proxy = bpy.data.objects.get(self.proxy_name)
            if not proxy:
                raise ValueError(f"Cannot get proxy object by name: \"{self.proxy_name}\"")
            target_mesh = bpy.data.objects.get(self.basis_mesh_name, None)
            if target_mesh is None:
                raise KeyError(f"Fit bones target mesh object ({self.basis_mesh_name}) is not found")

            final_mesh = bpy.data.objects.get(self.final_mesh_name, None)
            if final_mesh is None:
                raise KeyError(f"Fit bones final mesh object ({self.final_mesh_name}) is not found")
            
            basis_armature = bpy.data.objects.get(self.basis_armature_name, None)
            if basis_armature is None:
                raise KeyError(f"Fit bones basis armature object ({self.final_mesh_name}) is not found")
            armature = context.active_object
            ensure_objects_visible([proxy, target_mesh, final_mesh, basis_armature])
            bone_names = [bone.name for bone in armature.data.edit_bones if bone.select]
            transfer_rest_pose(basis_armature, armature, bone_names=bone_names)
            fit_bones(
                context=context,
                armature_object=armature,
                final_object=final_mesh,
                basis_object=target_mesh,
                proxy=proxy,
                bone_names=bone_names,
                lock_rotation=self.lock_rotation
            )
        except Exception as ex:
            print(traceback.format_exc())
            self.report(
                {'ERROR'}, f"Unable to transfer deform from proxy. See console for details"
            )
            return {'CANCELLED'}
        finally:
            state.restore_state()

        print("Fit Bones done")
        return {'FINISHED'}
    

classes = [MRF_OT_init_surface_deform_proxy, MRF_OT_init_mesh_deform_proxy, MRF_OT_fit_bones]
    

def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)


if __name__ == '__main__':
    register()
