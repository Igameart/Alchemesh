from typing import List
import bpy
import bmesh
from bpy.types import Context
from mathutils import Vector


def get_geometric_center(obj, material_name):
    """
    Calculate the geometric center of vertices associated with a given material.
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    material_index = next((i for i, mat in enumerate(obj.data.materials) if mat.name == material_name), None)

    if material_index is None:
        return None

    vertices = [vert.co for face in bm.faces if face.material_index == material_index for vert in face.verts]
    if not vertices:
        return None

    return sum(vertices, Vector()) / len(vertices)


def get_weighted_geometric_center(objects: List[bpy.types.Object]):
    """
    Calculates the weighted geometric center of a group of objects,
    based on the areas of their polygons.

    Args:
        objects (List[bpy.types.Object]): A list of Blender objects, which should be meshes.

    Returns:
        Optional[mathutils.Vector]: The weighted geometric center as a Vector, or None if the total area is zero.

    Note:
        This function assumes that all objects in the list are meshes. Non-mesh objects may lead to 
        unexpected behavior.
    """
    total_area = 0.0
    weighted_center = Vector()
    for obj in objects:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()

        for face in bm.faces:
            face_center = face.calc_center_median()
            face_area = face.calc_area()
            weighted_center += face_center * face_area
            total_area += face_area

        bm.free()

    if total_area == 0.0:
        return None

    return weighted_center / total_area


class MRF_OT_fit_geo_center(bpy.types.Operator):
    bl_idname = "meta_reforge.fit_geo_center"
    bl_label = "Fit Geometry Center"
    bl_description = "Fit bones to the center of the geometry associated with specified material"
    bl_options = {'REGISTER', 'UNDO'}

    object_name: bpy.props.StringProperty(name="Object Name", options={"HIDDEN"})

    def execute(self, context):        
        obj = bpy.data.objects.get(self.object_name, None)
        if not obj:
            raise ValueError(f"Cannot get object by name: \"{self.self.object_name}\"")
        center = get_weighted_geometric_center([obj])
        if center is None:
            self.report({'ERROR'}, "Material not found or no vertices with the material")
            return {'CANCELLED'}

        for bone in context.selected_bones:
            # freeze direction
            direction = bone.tail - bone.head
            # translate bone to the center
            bone.head = center
            # restore direction
            bone.tail = center + direction

        return {'FINISHED'}

def register():
    bpy.utils.register_class(MRF_OT_fit_geo_center)

def unregister():
    bpy.utils.unregister_class(MRF_OT_fit_geo_center)

if __name__ == "__main__":
    register()
