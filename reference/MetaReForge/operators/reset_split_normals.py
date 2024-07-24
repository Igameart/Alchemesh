import bpy
import bmesh
from typing import List
from bpy.types import Context
from mathutils.kdtree import KDTree
from mathutils import Vector
from ..utils.blender.unsorted import (
    duplicate_mesh_light,
    join_objects,
    merge_by_distance
)

from ..utils.blender.object import (
    ensure_objects_visible
)
from ..utils.blender.keep_state import EditorState


class SimpleVertex:
    def __init__(self, index: int, co: Vector, mesh_index: int) -> None:
        self.index = index
        self.co = co
        self.mesh_index = mesh_index

    @staticmethod
    def average_co(vertices: list) -> 'SimpleVertex':
        """
        Calculate the average coordinates of a list of vertices.

        Args:
            vertices (list): A list of SimpleVertex instances.

        Returns:
            Vector: The average coordinates of the given vertices.
        """
        s = None
        s = None
        for v in vertices:
            s = v.co.copy() if s is None else s + v.co
        return s / len(vertices)
    

def bmesh_from_object(obj: bpy.types.Object) -> bmesh.types.BMesh:
    """
    Create a BMesh from a given Blender object.

    Args:
        obj (bpy.types.Object): The Blender object to create BMesh from.

    Returns:
        bmesh.types.BMesh: The created BMesh.
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    return bm


def get_balanced_kd_from_vertices(vertices: bmesh.types.BMVertSeq):
    """
    Create a balanced KDTree from a sequence of BMVert.

    Args:
        vertices (bmesh.types.BMVertSeq): A sequence of BMVert.

    Returns:
        KDTree: The balanced KDTree.
    """
    kd = KDTree(size=len(vertices))
    for v in vertices:
        kd.insert(v.co, v.index)
    kd.balance()
    return kd
    

def batch_init_bmeshes(objects: list) -> list:
    """
    Initialize a list of BMeshes from a list of objects.

    Args:
        objects (list): A list of Blender objects.

    Raises:
        Exception: If any object is not of type 'MESH'.

    Returns:
        list: A list of initialized BMeshes.
    """
    bmeshes = [None] * len(objects)
    for mesh_index, obj in enumerate(objects):
        if obj.type != "MESH":
            raise Exception(f"{obj.name} is not MESH")
        bmeshes[mesh_index] = bmesh_from_object(obj)
    return bmeshes


def batch_init_kd_trees_from_bmeshes(bmeshes: list) -> list:
    """
    Initialize KD trees for each BMesh in a list.

    Args:
        bmeshes (list): A list of BMesh instances.

    Returns:
        list: A list of KDTree instances corresponding to each BMesh.
    """
    kd_trees = [None] * len(bmeshes)
    for mesh_index, bm in enumerate(bmeshes):
        kd_trees[mesh_index] = get_balanced_kd_from_vertices(bm.verts)
    return kd_trees


def transfer_split_normals(
        context: bpy.types.Context,
        source: bpy.types.Object,
        target: bpy.types.Object,
        vg_name: str = None
) -> None:
    """
    Transfer split normals from a source object to a target object using a Data Transfer modifier.

    This function adds a Data Transfer modifier to the target object to copy custom normals from the source. 
    If the target object does not have shape keys, a basis shape key is added. The normals are transferred based 
    on the nearest vertex, and the transfer can be limited to a specified vertex group.

    Args:
        source (bpy.types.Object): The object from which to transfer normals.
        target (bpy.types.Object): The object to which the normals are transferred.
        vg_name (str, optional): The name of the vertex group to limit the transfer. Defaults to None.
    """
    
    # Add a Data Transfer modifier to the target object
    modifier = target.modifiers.new(name="Data Transfer", type='DATA_TRANSFER')
    if not target.data.shape_keys:
        target.shape_key_add(name="Basis", from_mix=False)
    
    # Configure the modifier to transfer face corner data normals
    modifier.object = source
    modifier.data_types_loops = {'CUSTOM_NORMAL'}
    modifier.loop_mapping = 'NEAREST_POLYNOR'
    modifier.vertex_group = vg_name if vg_name else ""

    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    context.view_layer.objects.active = target
    
    # Move the modifier to the top of the stack
    if target.modifiers.find(modifier.name) > 0:
        bpy.ops.object.modifier_move_to_index(modifier=modifier.name, index=0)
    
    # Apply the modifier to make changes permanent
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def recompute_split_normals_as_merged(
        context: bpy.types.Context,
        objects: List[bpy.types.Object],
        locked_indices: List[int],
        merge_distance: float
) -> None:
    """
    Recomputes split normals....

    Args:
        
    Raises:

    """
    
    duplicated = []
    # Duplicate each object for processing
    for obj in objects:
        new_obj = duplicate_mesh_light(context, obj)
        duplicated.append(new_obj)
        
    # Merge duplicated objects into a single proxy object
    if len(duplicated) >= 2:
        proxy = join_objects(duplicated)
    elif len(duplicated) == 1:
        proxy = duplicated[0]
    else:
        raise Exception("No object")
    
    # Merge vertices of the proxy object by the specified distance
    merge_by_distance(proxy, threshold=merge_distance, boundary_edges=True)
    
    # Reset proxy's split normals
    bpy.context.view_layer.objects.active = proxy
    bpy.ops.mesh.customdata_custom_splitnormals_clear()

    if hasattr(proxy.data, "auto_smooth_angle"):
        proxy.data.auto_smooth_angle = 3.14
    
    # Transfer split normals from the proxy to each original object
    for index, obj in enumerate(objects):
        if index not in locked_indices:
            transfer_split_normals(context, source=proxy, target=obj)
            for locked_index in locked_indices:
                locked_obj = objects[locked_index]
                transfer_split_normals_from_seam(context, locked_obj, obj, merge_distance=merge_distance)
    
    # Remove the proxy object after transfer
    bpy.data.objects.remove(proxy, do_unlink=True)


def transfer_split_normals_from_seam(
        context: bpy.types.Context,
        source_obj: bpy.types.Object,
        target_obj: bpy.types.Object,
        merge_distance: float
) -> None:

    """
    Transfer split normals from a source object to a target object, 
    focusing on vertices near seams within a specified merge distance.

    This function finds vertices in the target object that are within the merge distance
    from any vertex in the source object. It then creates a vertex group in the target object
    containing these vertices and uses it to limit the transfer of split normals from the 
    source to the target object.

    Args:
        source_obj (bpy.types.Object): The object from which to transfer normals.
        target_obj (bpy.types.Object): The object to which the normals are transferred.
        merge_distance (float): The distance within which vertices are considered for normal transfer.
    """
    # Create bmesh objects from the source and target and KD tree for easy access to vertex data
    source_kd = get_balanced_kd_from_vertices(source_obj.data.vertices)
    # Find target vertices close to any source vertex
    vg_indices = set()
    for vertex in target_obj.data.vertices:
        if len(source_kd.find_range(vertex.co, merge_distance)) != 0:
            vg_indices.add(vertex.index)
    
    # Make sure target object is selected and active
    bpy.ops.object.select_all(action="DESELECT")
    target_obj.select_set(True)
    context.view_layer.objects.active = target_obj

    # Create or replace a vertex group in the target object
    vg_name = "MetaReforge.SeamVertices"
    vg = target_obj.vertex_groups.get(vg_name)
    if vg:
        target_obj.vertex_groups.remove(vg)
    vg = target_obj.vertex_groups.new(name=vg_name)
    
    target_obj.data.update()
    bpy.context.view_layer.update()
    
    # Add identified vertices to the vertex group
    vg.add(list(vg_indices), 1.0, 'REPLACE')
    
    # Transfer normals using the created vertex group
    transfer_split_normals(context, source=source_obj, target=target_obj, vg_name=vg.name)
    
    target_obj.data.update()
    bpy.context.view_layer.update()

    vg = target_obj.vertex_groups.get(vg_name)
    # Remove the temporary vertex group after transfer
    if vg:
        target_obj.vertex_groups.remove(vg)


def alight_seam(
        objects: List[bpy.types.Object],
        locked_indices: List[int] = None,
        threshold: float = 0.01
) -> None:
    """
    Align vertices of multiple objects based on proximity and locked vertices.

    This function finds vertices within a specified threshold distance across multiple objects.
    It aligns these vertices to a new position, either an average position or the position of locked vertices,
    based on the locked indices provided.

    Args:
        objects (List[bpy.types.Object]): A list of objects to process.
        locked_indices (List[int], optional): Indices of vertices that should not be moved. Defaults to None.
        threshold (float, optional): Distance threshold to consider vertices for alignment. Defaults to 0.01.
    """

    print(f"Aligning vertices of " + ", ".join(obj.name for obj in objects))
    n = len(objects)
    bmeshes = batch_init_bmeshes(objects)
    kd_trees = batch_init_kd_trees_from_bmeshes(bmeshes)

    # Find duplicates and align vertices
    new_vertices = [dict() for _ in range(n)]
    processed_vertices = [set() for _ in range(n)]
    for bm in bmeshes:
        # Search for vertices within the threshold
        for bm_vert in bm.verts:
            vertices_to_move = []
            locked_vertices = []
            for mesh_index, kd in enumerate(kd_trees):
                for (co, vertex_index, dist) in kd.find_range(bm_vert.co, threshold):
                    if vertex_index not in processed_vertices[mesh_index]:
                        vertex = SimpleVertex(vertex_index, co, mesh_index)
                        if locked_indices and mesh_index in locked_indices:
                            locked_vertices.append(vertex)
                        else:
                            vertices_to_move.append(vertex)
                        processed_vertices[mesh_index].add(vertex_index)
            
            # Determine new position for vertices to move
            if len(vertices_to_move) > 1:
                new_position = None
                if len(locked_vertices) == 0:
                    new_position = SimpleVertex.average_co(vertices_to_move)
                elif len(locked_vertices) == 1:
                    new_position = locked_vertices[0].co
                else:
                    new_position = SimpleVertex.average_co(locked_vertices)

                if new_position:
                    for vertex in vertices_to_move:
                        new_vertices[vertex.mesh_index][vertex.index] = new_position   
        
    # Apply new positions to the vertices
    for mesh_index, new_coordinates in enumerate(new_vertices):
        bm = bmeshes[mesh_index]
        for index, co in new_coordinates.items():
            bm.verts[index].co = co

    # Apply changes from BMesh to scene objects
    # for i, obj in enumerate(objects):
    #     bmeshes[i].to_mesh(obj.data)
    #     bmeshes[i].free()
    #     obj.data.update()
    
    bpy.context.view_layer.update()
    print("Aligning complete!")


def recompute_split_normals(
        context: bpy.types.Context,
        objects: List[bpy.types.Object],
        locked_indices: List[int] = None,
        merge_distance: float = 0.001
) -> None:
    """
    Recompute custom split normals for head and body objects.

    This function handles different scenarios based on the presence of head and body objects and 
    whether the body's normals are locked. It transfers split normals either from merged objects 
    or from seams, depending on the given conditions.

    Args:
        context (bpy.types.Context): The current Blender context.
        head_obj (bpy.types.Object, optional): The head object to process. Defaults to None.
        body_obj (bpy.types.Object, optional): The body object to process. Defaults to None.
        body_lock (bool, optional): Whether the body's normals are locked. Defaults to False.
        merge_distance (float, optional): The distance within which to merge vertices. Defaults to 0.001.

    Raises:
        Exception: If no objects are specified.
    """
    obj_str = ", ".join(
        [f"{obj.name} (locked)" if i in locked_indices else obj.name for i, obj in enumerate(objects)]
    )
    print(f"Recomputing custom split normals: {obj_str}")

    recompute_split_normals_as_merged(
        context=context,
        objects=objects,
        locked_indices=locked_indices,
        merge_distance=merge_distance
    )
    
    print("Recomputing complete!")


class MRF_OT_recompute_split_normals(bpy.types.Operator):
    bl_idname = "meta_reforge.recompute_split_normals"
    bl_label = "Re-Compute Split Normals"
    bl_options = {'REGISTER', 'UNDO'}

    align_vertices: bpy.props.BoolProperty(name="Align Vertices", default=True, options={"HIDDEN"})
    weld_distance: bpy.props.FloatProperty(name="Weld Distance", default=1e-2, options={"HIDDEN"})
     
    @classmethod
    def poll(cls, context: Context):
        config = context.scene.meta_reforge_config
        if len(config.fbx_head_lods) == 0 and len(config.fbx_body_lods) == 0:
            return False
        return True

    def execute(self, context: bpy.types.Context):
        config = context.scene.meta_reforge_config
        
        state = EditorState.capture_current_state()
        ensure_objects_visible(config.get_associated_objects())
    
        lods = dict()
        # Add head meshses to LOD batches
        for lod_index, lod_item in enumerate(config.fbx_head_lods):
            lod_batches = lods.get(lod_index, None)
            if lod_batches is None:
                lod_batches = lods[lod_index] = dict()
            for mesh_item in lod_item.mesh_items:
                batch = lod_batches.get(mesh_item.edit_id, None)
                if batch is None:
                    batch = lod_batches[mesh_item.edit_id] = list()
                batch.append(mesh_item.final_object)

        # Add body meshses to LOD batches
        if len(config.fbx_body_lods) == 0:
            body_lods = []
        elif len(config.fbx_head_lods) // len(config.fbx_body_lods) == 2:
            body_lods = [lod_item for lod_item in config.fbx_body_lods for _ in range(2)]
        else:
            body_lods = [lod_item for lod_item in config.fbx_body_lods]

        for lod_index, lod_item in enumerate(body_lods):
            lod_batches = lods.get(lod_index, None)
            if lod_batches is None:
                lod_batches = lods[lod_index] = dict()
            for mesh_item in lod_item.mesh_items:
                batch = lod_batches.get(mesh_item.edit_id, None)
                if batch is None:
                    batch = lod_batches[mesh_item.edit_id] = list()
                batch.append(mesh_item.final_object)

        processed_objects = set()
        for lod_index, lod in lods.items():
            print(f"----------{lod_index}----------")
            for edit_id, batch in lod.items():
                locked_indices = [i for i, obj in enumerate(batch) if obj in processed_objects]
                if self.align_vertices:
                    alight_seam(batch, locked_indices, threshold=self.weld_distance)
                recompute_split_normals(context, batch, locked_indices, merge_distance=self.weld_distance)
                processed_objects.update(batch)   

        state.restore_state()
        return {'FINISHED'}
    

def register():
    bpy.utils.register_class(MRF_OT_recompute_split_normals)  


def unregister():
    bpy.utils.unregister_class(MRF_OT_recompute_split_normals)  


if __name__ == '__main__':
    register()
