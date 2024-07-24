import bpy
from mathutils import Vector, Matrix
from typing import List


def matrix_from_axes(center: Vector, x_axis: Vector, y_axis: Vector, z_axis: Vector) -> Matrix:
    """
    Constructs a 4x4 transformation matrix using the provided axes and center.

    This function requires that the input axes be orthogonal and normalized.
    The resulting matrix uses the axes for the first three columns and the center 
    for the fourth column, representing the translation.

    Args:
        center (Vector): A vector representing the translation (center point) of the matrix.
        x_axis (Vector): A vector representing the x-axis.
        y_axis (Vector): A vector representing the y-axis.
        z_axis (Vector): A vector representing the z-axis.

    Returns:
        Matrix: A 4x4 transformation matrix where the first three columns represent
                the x, y, and z axes respectively, and the fourth column represents 
                the translation (center point).
    """
    return Matrix(
        [
            [x_axis.x, y_axis.x, z_axis.x, center.x],
            [x_axis.y, y_axis.y, z_axis.y, center.y],
            [x_axis.z, y_axis.z, z_axis.z, center.z],
            [0, 0, 0, 1]
        ]
    )


class Octa:
    def __init__(self, center: Vector, vertices: List[Vector]):
        self.center = center
        self.vertices = vertices

    def to_matrix(self) -> Matrix:
        return Octa._matrix_from_octa(self.center, [v - self.center for v in self.vertices])


    @staticmethod
    def from_bone(bone: bpy.types.EditBone, offset: float):
        temp = Octa(
            bone.head,
            [bone.head + o for o in Octa._octa_offsets_from_bone(bone, offset)]
        )
        return temp
    
    @staticmethod
    def average(structures: List["Octa"], weights: List[float]) -> "Octa":
        center = Vector([0, 0, 0])
        vertices = []
        for i in range(6):
            vertices.append(Vector([0, 0, 0]))
        total_weight = 0.0
        for w, item in zip(weights, structures):
            center += item.center * w
            total_weight += w
            for total, vertex in zip(vertices, item.vertices):
                total += vertex * w

        center /= total_weight
        for vertex in vertices:
            vertex /= total_weight

        return Octa(center, vertices)
    
    @staticmethod
    def _octa_offsets_from_bone(bone: bpy.types.EditBone, offset: float) -> List[Vector]:
        """
        Computes offsets along the bone's local axes to form an octahedral structure 
        centered around the bone's head.

        Args:
            bone: The bone object from which the offsets will be derived.
            offset: The distance from the bone's head in each direction.

        Returns:
            A list of offsets along the bone's local axes (X, -X, Y, -Y, Z, -Z) in 
            object coordinates.
        """
        offsets_bone_local = [
            (offset, 0.0, 0.0),   # positive X
            (-offset, 0.0, 0.0),  # negative X
            (0.0, offset, 0.0),   # positive Y   
            (0.0, -offset, 0.0),  # negative Y
            (0.0, 0.0, offset),   # positive Z
            (0.0, 0.0, -offset)   # negative Z
        ]
        return [bone.matrix.to_3x3() @ Vector(offset) for offset in offsets_bone_local]
    
    @staticmethod
    def _matrix_from_octa(center: Vector, offsets: List[Vector]) -> Matrix:
        """
        Computes a transformation matrix derived from a center point and octahedral offsets.

        This static method determines orthogonal axes (X, Y, Z) from the provided 
        octahedral offsets, ensuring that the axes are perpendicular to each other and
        constructs a transformation matrix using these axes and the center point.

        Args:
            center (Vector): The central point of the octahedral structure.
            offsets (List[Vector]): List of offsets from the center representing the vertices
            of the octahedron.

        Returns:
            Matrix: A transformation matrix constructed from the derived orthogonal axes
            and the center point.
        """   
        positive_x = offsets[0]
        negative_x = offsets[1]
        positive_y = offsets[2]
        negative_y = offsets[3]
        positive_z = offsets[4]
        negative_z = offsets[5]

        # Find variants of the positive X axis using perpendicular vectors
        derived_x1 = positive_y.cross(positive_z).normalized()
        derived_x2 = positive_z.cross(negative_y).normalized()
        derived_x3 = negative_y.cross(negative_z).normalized()
        derived_x4 = negative_z.cross(positive_y).normalized()

        # Calculate x-axis as an average of directly derived vectors and additional weighted vectors
        derived_x = (derived_x1 + derived_x2 + derived_x3 + derived_x4).normalized()
        x_axis = (positive_x - negative_x + 2 * derived_x).normalized()

        # Derive temporary Y-axis vectors based on the other axes 
        derived_y1 = positive_z.cross(x_axis).normalized()
        derived_y2 = x_axis.cross(negative_z).normalized()
        derived_y = (derived_y1 + derived_y2).normalized()

        # Calculate temporary Y-axis as an average; however, this isn't the final Y-axis
        # since it's not guaranteed to be perpendicular to the other axes
        temp_y_axis = (positive_y - negative_y + 2 * derived_y).normalized()

        # Determine the Z-axis to be perpendicular to the X-axis using vector products
        z_axis = x_axis.cross(temp_y_axis).normalized()

        # Refine the Y-axis to ensure all axes are orthogonal
        y_axis = z_axis.cross(x_axis).normalized()
        return matrix_from_axes(center, x_axis, y_axis, z_axis)
