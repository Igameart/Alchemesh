import bpy
import math
from mathutils import Vector
from typing import List
from .octa import Octa



class BarrycentricTriangle:
    def __init__(
            self,
            tri_old: List[bpy.types.MeshVertex],
            tri_new: List[bpy.types.MeshVertex]
        ):
        self.a1 = tri_old[0]
        self.b1 = tri_old[1]
        self.c1 = tri_old[2]

        self.a2 = tri_new[0]
        self.b2 = tri_new[1]
        self.c2 = tri_new[2]

        self.v0 = self.b1 - self.a1
        self.v1 = self.c1 - self.a1
        self.d00 = self.v0.dot(self.v0)
        self.d01 = self.v0.dot(self.v1)
        self.d11 = self.v1.dot(self.v1)
        self.denom = self.d00 * self.d11 - self.d01 * self.d01
        if abs(self.denom) <= 1e-8:
            # nothing to do with the triangle
            self.valid = False
        else:
            self.valid = True

        # Находим нормали к треугольникам
        ba1, ca1 = self.b1 - self.a1, self.c1 - self.a1
        ba2, ca2 = self.b2 - self.a2, self.c2 - self.a2
        self.normal_old = ba1.cross(ca1)
        self.normal_new = ba2.cross(ca2)

    def calc_triangle_weight(self) -> float:
        """
        Determines the area of the triangle ABC on the UV plane.
        """
        ab = (self.b1 - self.a1).length
        bc = (self.c1 - self.b1).length
        ac = (self.c1 - self.a1).length
        semi_abc = (ab + bc + ac) / 2
        area_sq = semi_abc * (semi_abc - ab) * (semi_abc - bc) * (semi_abc - ac)
        area = math.sqrt(max(0.0, area_sq))

        equilateral_area = math.sqrt(3) / 4 * math.pow(max(ab, bc, ac), 2)
        return area / equilateral_area
            

    def barycentric_coords(self, p):
        v2 = p - self.a1
        d20 = v2.dot(self.v0)
        d21 = v2.dot(self.v1)
        v = (self.d11 * d20 - self.d01 * d21) / self.denom
        w = (self.d00 * d21 - self.d01 * d20) / self.denom
        u = 1.0 - v - w
        return u, v, w
    
    def deform_vertex_with_offset(self, v_old):
        """Перенести деформацию с tri_old на tri_new для заданной вершины v_old с учетом смещения от плоскости."""
        # Вычисляем барицентрические координаты
        u, v, w = self.barycentric_coords(v_old)
        v_new_base = u * self.a2 + v * self.b2 + w * self.c2
        
        # Вычисляем расстояние от v_old до плоскости tri_old
        temp = v_old - self.a1
        distance = temp.dot(self.normal_old) / self.normal_old.length
        
        # Добавляем смещение к v_new
        v_new = v_new_base + distance * (self.normal_new / self.normal_new.length)
        
        return Vector(v_new)
    
    def deform_structure(self, structure: Octa):
        center = self.deform_vertex_with_offset(structure.center)
        vertices = []
        for vertex in structure.vertices:
            new_vertex = self.deform_vertex_with_offset(vertex)
            vertices.append(new_vertex)
        return Octa(center, vertices)