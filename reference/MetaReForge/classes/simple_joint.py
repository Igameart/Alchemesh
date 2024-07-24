import bpy
from typing import List


class Joint:
    def __init__(self, edit_bone: bpy.types.EditBone) -> None:
        self.name = edit_bone.name
        parent = edit_bone.parent
        self.parent = None if parent is None else parent.name
        self.matrix = edit_bone.matrix.copy()

    @staticmethod
    def from_edit_bones(edit_bones: bpy.types.ArmatureEditBones) -> List["Joint"]:
        joints = []
        for bone in edit_bones:
            joints.append(Joint(bone))
        return joints


class JointsCollection:
    def __init__(self) -> None:
        self.data = dict()

    def add(self, joint: Joint) -> None:
        if joint.name not in self.data:
            self.data[joint.name] = joint
            return

        existing_joint = self.data[joint.name]
        if existing_joint.parent != joint.parent and joint.parent is not None:
            if existing_joint.parent is not None:
                raise Exception("Invalid hierarcy. Parents are not matching")
            existing_joint.parent = joint.parent
        # DO SOME CHECK OF TRANSFORMS
