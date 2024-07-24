import bpy
import mathutils
from typing import List


def add_surface_deform_modifier(
        context: bpy.types.Context,
        obj: bpy.types.Object,
        name: str,
        target: bpy.types.Object,
        falloff: float = 4.0,
        strength: float = 1.0,
        ovewrite_if_exists: bool = False
    ) -> bpy.types.SurfaceDeformModifier:
    """
    Adds a Surface Deform modifier to an object and binds it to a target.

    This function creates a Surface Deform modifier with specified parameters and attempts to bind it to the given target object. If 'ovewrite_if_exists' is True, it will replace any existing modifier with the same name.

    Args:
        obj (bpy.types.Object): The object to which the modifier is added.
        name (str): The name of the modifier.
        target (bpy.types.Object): Mesh object to deform with.
        falloff (float, optional): Controls how much nearby polygons influence deformation. Default is 4.0. Min=2, Max=16
        strength (float, optional): Strength of modifier deformations. Default is 1.0. Min = -100, Max = 100
        ovewrite_if_exists (bool, optional): Whether to replace the modifier if it already exists. Default is False.

    Returns:
        bpy.types.SurfaceDeformModifier: The created or modified Surface Deform modifier.
    """
    if context:
        context.view_layer.objects.active = obj
    else:
        bpy.context.view_layer.objects.active = obj
    if ovewrite_if_exists:
        modifier = obj.modifiers.get(name)
        if modifier:
            obj.modifiers.remove(modifier)
    modifier = obj.modifiers.new(name=name, type="SURFACE_DEFORM")
    modifier.target = target
    modifier.falloff = falloff
    modifier.strength = strength
    bpy.ops.object.surfacedeform_bind(modifier=modifier.name)
    return modifier

def remove_shape_key(obj: bpy.types.Object, shape_key_name: str) -> None:
    if obj.type != "MESH":
        raise ValueError("Provided object is not a mesh")
    if obj.data.shape_keys:
        sk = obj.data.shape_keys.key_blocks.get(shape_key_name)
        if sk:
            obj.shape_key_remove(sk)


def add_new_shape_key(
        obj: bpy.types.Object,
        shape_key_name: str,
        from_mix: bool = False,
        replace: bool = False
) -> bpy.types.ShapeKey:
    
    if obj.type != "MESH":
        raise ValueError("Provided object is not a mesh")
    if not obj.data.shape_keys:
        obj.shape_key_add(name='Basis', from_mix=False)
    if replace:
        remove_shape_key(obj, shape_key_name)
        obj.data.update()
    shape_key = obj.shape_key_add(name=shape_key_name, from_mix=from_mix)
    return shape_key
    

def join_as_shape(
        source_obj: bpy.types.Object,
        target_object: bpy.types.Object,
        shape_key_name: str = None,
        replace: bool = False
) -> bpy.types.ShapeKey:
    
    if not shape_key_name:
        shape_key_name = source_obj.name

    if not target_object.data.shape_keys:
        target_object.shape_key_add(name='Basis', from_mix=False)
    sk = add_new_shape_key(target_object, shape_key_name, from_mix=False, replace=replace)
    # Transfer vertex positions from the target object to the new shape key
    for i, vertex in enumerate(source_obj.data.vertices):
        # Apply the vertex position from the target object to the new shape key
        sk.data[i].co = vertex.co
    return sk

def get_deformed_vertices(context: bpy.types.Context, obj: bpy.types.Object) -> List[mathutils.Vector]:
    # Get an evaluated version of the object (with modifiers applied)
    dg = context.evaluated_depsgraph_get()
    temp_obj = obj.evaluated_get(dg)

    return temp_obj.data.vertices


# def rebase_shape_keys_shapekey(
#         context: bpy.types.Context,
#         source_obj: bpy.types.Object,
#         target_obj: bpy.types.Object,
#         shape_keys: list
#     ) -> None:

#     bpy.ops.object.select_all(action="DESELECT")
#     context.view_layer.objects.active = source_obj
#     source_obj.select_set(True)
#     deformer = None
#     sk_source_base = join_as_shape(target_obj, source_obj, "SOURCE_BASE", replace=True)
#     sk_source_base.value = 1.0
#     new_shape_key_names = []
#     for index, sk_name in enumerate(shape_keys):
#         print(sk_name)
#         sk_source = source_obj.data.shape_keys.key_blocks.get(sk_name)
#         if sk_source is None:
#             print(f"No {sk_name} shape key for {source_obj.name}")
#             continue

#         sk_source.value = 1.0
#         sk_target = add_new_shape_key(target_obj, sk_source.name, from_mix=False, replace=True)

#         deformer = add_surface_deform_modifier(
#             context,
#             source_obj,
#             name='MRF_SURFACE_DEFORM',
#             target=target_obj,
#             ovewrite_if_exists=True
#         )
#         if not deformer.is_bound:
#             raise Exception("Unable to bind Surface Deform modifier")
        
#         sk_source_base.value = 0.0
#         new_data = get_deformed_vertices(context, source_obj)
#         for index, v in enumerate(sk_target.data):
#             v.co = new_data[index].co
#         sk_source.value = 0.0
#         new_shape_key_names.append(sk_target.name)

#     if deformer:
#         source_obj.modifiers.remove(deformer)
#     sk_source_base.value = 0.0


def rebase_shape_keys_shapekey(
        context: bpy.types.Context,
        source_obj: bpy.types.Object,
        target_obj: bpy.types.Object,
        shape_keys: list
    ) -> None:

    context.view_layer.objects.active = source_obj
    source_verts = source_obj.data.vertices
    target_verts = target_obj.data.vertices
    new_shape_key_names = []
    for index, sk_name in enumerate(shape_keys):
        print(sk_name)
        sk_source = source_obj.data.shape_keys.key_blocks.get(sk_name)
        sk_target = add_new_shape_key(target_obj, sk_source.name, from_mix=False, replace=True)

        for index, v in enumerate(sk_target.data):
            delta = sk_source.data[index].co - source_verts[index].co
            
            n1 = target_verts[index].normal
            n2 = source_verts[index].normal
            rotation_diff = n2.rotation_difference(n1)

            # Применяем вращение к дельта-вектору
            rotated_delta = rotation_diff @ delta

            v.co = target_verts[index].co + rotated_delta
        new_shape_key_names.append(sk_target.name)


def scale_shape_key_deltas(
    ref_object: bpy.types.Object,
    target_object: bpy.types.Object,
    influence: float,
    shape_keys: list
) -> None:
    # Go through all edges and to have a dict {vertext_index: [edge]}
    ref_mesh = ref_object.data

    ref_edge_lengths = dict()
    for i in range(len(ref_mesh.vertices)):
        ref_edge_lengths[i] = list()

    for edge in ref_mesh.edges:
        v1_idx, v2_idx = edge.vertices[0], edge.vertices[1]
        v1, v2 = ref_mesh.vertices[v1_idx], ref_mesh.vertices[v2_idx]
        length = (v2.co - v1.co).length
        ref_edge_lengths[v1_idx].append(length)
        ref_edge_lengths[v2_idx].append(length)

    target_mesh = target_object.data

    target_edge_lengths = dict()
    for i in range(len(target_mesh.vertices)):
        target_edge_lengths[i] = list()

    for edge in target_mesh.edges:
        v1_idx, v2_idx = edge.vertices[0], edge.vertices[1]
        v1, v2 = target_mesh.vertices[v1_idx], target_mesh.vertices[v2_idx]
        length = (v2.co - v1.co).length
        target_edge_lengths[v1_idx].append(length)
        target_edge_lengths[v2_idx].append(length)

    
    multipliers = []
    for idx in range(len(ref_edge_lengths)):
        ref_len = ref_edge_lengths[idx]
        target_len = target_edge_lengths[idx]
        ratios = [tl / rl if abs(rl) >= 1e-7 else 1.0 for rl, tl in zip(ref_len, target_len)]
        mul = sum(ratios) / len(ratios)
        mul = min(ratios)
        multipliers.append(mul)

    for sk_name in shape_keys:
        print(sk_name)
        sk = target_obj.data.shape_keys.key_blocks.get(sk_name)
        if sk is None:
            print(f"No {sk_name} shape key for {target_obj.name}")
            continue
        
        for v_b, v_sk, mul in zip(target_obj.data.vertices, sk.data, multipliers):
            new_co = v_b.co + (v_sk.co - v_b.co) * ((mul - 1) * influence + 1)
            v_sk.co = new_co


def smooth_shape_keys(
        context: bpy.types.Context,
        obj: bpy.types.Object,
        shape_keys: list,
        factor: float = 0.5,
        iterations: float = 5,
        scale: float = 1.0,
        smooth_type: str = "SIMPLE",


) -> None:
    new_shape_key_names = []
    smooth_mod = obj.modifiers.new(name="CORRECTIVE_SMOOTH", type="CORRECTIVE_SMOOTH")
    smooth_mod.factor = factor
    smooth_mod.iterations = iterations
    smooth_mod.scale = scale
    smooth_mod.smooth_type = smooth_type
    
    for sk_name in shape_keys:
        print(sk_name)
        sk = obj.data.shape_keys.key_blocks.get(sk_name)
        if sk is None:
            print(f"No {sk_name} shape key for {obj.name}")
            continue
        
        sk.value = 1.0
        new_data = get_deformed_vertices(context, obj)
        corrected_co = [v.co.copy() for v in new_data]
        for v_sk, corr_co in zip(sk.data, corrected_co):
            v_sk.co = corr_co
        sk.value = 0.0
        new_shape_key_names.append(sk.name)
    
    obj.modifiers.remove(smooth_mod)


source_obj = bpy.data.objects["source"]
target_obj = bpy.data.objects["target"]

shape_keys = [sk.name for i, sk in enumerate(source_obj.data.shape_keys.key_blocks) if i != 0]

rebase_shape_keys_shapekey(
    bpy.context,
    source_obj,
    target_obj,
    shape_keys
)

scale_shape_key_deltas(
     ref_object=source_obj,
     target_object=target_obj,
     influence=1,
     shape_keys=shape_keys
)

smooth_shape_keys(
     bpy.context,
     target_obj,
     shape_keys
)
