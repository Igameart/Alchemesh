import bpy
import math
from mathutils import Euler, Vector, Matrix
from .io import get_reader
from .libimport import dna, dnacalib, vtx_color
from ..utils.common import limit


def init_material(obj: bpy.types.Object, name: str):
	# Check if the object is a mesh
	if obj.type != 'MESH':
		raise TypeError("Provided object is not a mesh")

	# Create a new material
	material = bpy.data.materials.get(name)
	if material is None:
		material = bpy.data.materials.new(name=name)

	# Check if the object already has a material slot
	if obj.data.materials:
		# Assign to the first material slot
		obj.data.materials[0] = material
	else:
		# Add a material slot and assign the material
		obj.data.materials.append(material)
	return material


if dna and dnacalib:
	def get_py_vert_positions_from_dna(reader: "dna.BinaryStreamReader", mesh_index: int) -> list:
		x = reader.getVertexPositionXs(mesh_index)
		y = reader.getVertexPositionYs(mesh_index)
		z = reader.getVertexPositionZs(mesh_index)
		
		positions = []
		for vertex_index in reader.getVertexLayoutPositionIndices(mesh_index):
			position = Vector((x[vertex_index], y[vertex_index], z[vertex_index]))
			positions.append(position)
		return positions
	
	def get_py_vtx_color_values(reader: "dna.BinaryStreamReader", mesh_index: int, vtc_color_values: list = None) -> list:
		colors = []
		for vertex_index in reader.getVertexLayoutPositionIndices(mesh_index):
			colors.append(vtc_color_values[vertex_index])
		return colors


	def get_py_vert_normals_from_dna(reader: "dna.BinaryStreamReader", mesh_index: int) -> list:
		x = reader.getVertexNormalXs(mesh_index)
		y = reader.getVertexNormalYs(mesh_index)
		z = reader.getVertexNormalZs(mesh_index)
		normals = []
		for normal_index in reader.getVertexLayoutNormalIndices(mesh_index):
			normal = Vector((x[normal_index], y[normal_index], z[normal_index]))
			normal.normalize()
			# Append normalized normal vector
			normals.append(normal)
		return normals


	def get_py_vert_uvs_from_dna(reader: "dna.BinaryStreamReader", mesh_index: int) -> list:
		u = reader.getVertexTextureCoordinateUs(mesh_index)
		v = reader.getVertexTextureCoordinateVs(mesh_index)
		uvs = []
		for uv_index in reader.getVertexLayoutTextureCoordinateIndices(mesh_index):
			uvs.append((u[uv_index], v[uv_index]))
		return uvs


	def get_py_vertex_groups_from_dna(reader: "dna.BinaryStreamReader", mesh_index: int) -> dict:
		vertex_groups = dict()
		for layout_index, vertex_index in enumerate(reader.getVertexLayoutPositionIndices(mesh_index)):
			vertex_joints = reader.getSkinWeightsJointIndices(mesh_index, vertex_index)
			vertex_weights = reader.getSkinWeightsValues(mesh_index, vertex_index)
			for joint_index, weight in zip(vertex_joints, vertex_weights):
				if joint_index in vertex_groups:
					group_indices, group_weights = vertex_groups[joint_index]
				else:
					group_indices, group_weights = [], []
					vertex_groups[joint_index] = group_indices, group_weights

				group_indices.append(layout_index)
				group_weights.append(weight)
		return vertex_groups


	def get_py_faces_from_dna(reader: "dna.BinaryStreamReader", mesh_index: int) -> list:
		faces = []
		for face_index in range(reader.getFaceCount(mesh_index)):
			face = reader.getFaceVertexLayoutIndices(mesh_index, face_index)
			faces.append(face)
		return faces


	def get_shape_keys_from_dna(reader: "dna.BinaryStreamReader", mesh_index: int) -> dict:

		map = dict()
		shape_targets = dict()
		for layout_index, vertex_index in enumerate(reader.getVertexLayoutPositionIndices(mesh_index)):
			if vertex_index in map:
				map[vertex_index].append(layout_index)
			else:
				map[vertex_index] = [layout_index]

		for target_index in range(reader.getBlendShapeTargetCount(mesh_index)):
			delta_xs = reader.getBlendShapeTargetDeltaXs(mesh_index, target_index)
			delta_ys = reader.getBlendShapeTargetDeltaYs(mesh_index, target_index)
			delta_zs = reader.getBlendShapeTargetDeltaYs(mesh_index, target_index)
			vertex_indices = reader.getBlendShapeTargetVertexIndices(mesh_index, target_index)
			channel_index = reader.getBlendShapeChannelIndex(mesh_index, target_index)
			channel_name = reader.getBlendShapeChannelName(channel_index)
			deltas = dict()
			for vertex_index, delta_x, delta_y, delta_z in zip(vertex_indices, delta_xs, delta_ys, delta_zs):
				for layout_index in map[vertex_index]:
					deltas[layout_index] = (delta_x, delta_y, delta_z)

			shape_targets[channel_name] = deltas

		return shape_targets


	def build_meshes(
			dna_reader: 'dna.BinaryStreamReader',
			lod0_only: bool = False,
			apply_transforms: bool = False,
			shape_key_threshold: float = 0.015
	) -> list:
		mesh_shader_mapping = {m: s for s, meshes in vtx_color.MESH_SHADER_MAPPING.items() for m in meshes}
		mesh_lod_map = dict()
		objects = dict()
		for lod_index in range(10):
			mesh_indices = dna_reader.getMeshIndicesForLOD(lod_index)
			for mesh_index in mesh_indices:
				mesh_lod_map[mesh_index] = lod_index
		
		for mesh_index in range(dna_reader.getMeshCount()):
			lod_index = mesh_lod_map.get(mesh_index, 0)
			mesh_name = dna_reader.getMeshName(mesh_index)
			vtx_color_mesh_index = vtx_color.VTX_COLOR_MESHES.index(mesh_name)
			vtx_color_values = vtx_color.VTX_COLOR_VALUES[vtx_color_mesh_index]
			vtx_color_values = [[limit(c, 0.0, 1.0) for c in color] + [1.0] for color in vtx_color_values]
			verts = get_py_vert_positions_from_dna(dna_reader, mesh_index)
			colors = get_py_vtx_color_values(dna_reader, mesh_index, vtx_color_values)
			faces = get_py_faces_from_dna(dna_reader, mesh_index)
			normals = get_py_vert_normals_from_dna(dna_reader, mesh_index)
			uvs = get_py_vert_uvs_from_dna(dna_reader, mesh_index)
			vertex_groups = get_py_vertex_groups_from_dna(dna_reader, mesh_index)
			
			if lod0_only and "lod0" not in mesh_name:
				continue
			# Create a new mesh object
			mesh = bpy.data.meshes.new(name="Mesh")
			obj = bpy.data.objects.new(mesh_name, mesh)

			# Link it to the scene
			bpy.ops.object.select_all(action="DESELECT")
			bpy.context.collection.objects.link(obj)
			bpy.context.view_layer.objects.active = obj
			obj.select_set(True)

			# Create the mesh data
			mesh.from_pydata(verts, [], faces)
			# Update the mesh and recalculate normals
			mesh.update()

			# Create a vertex color layer
			if len(mesh.vertex_colors) == 0:
				mesh.vertex_colors.new()

			color_layer = mesh.vertex_colors.active

			# Set smooth shading for polygons
			for poly in mesh.polygons:
				poly.use_smooth = True
				for _, loop_idx in enumerate(poly.loop_indices):
					loop_vert_idx = mesh.loops[loop_idx].vertex_index
					color_layer.data[loop_idx].color = colors[loop_vert_idx]  # Adding alpha value

			# Create split normals
			if hasattr(mesh, "use_auto_smooth"):
				# blender <4.1
				mesh.use_auto_smooth = False
				mesh.create_normals_split()
				mesh.normals_split_custom_set([normals[l.vertex_index] for l in mesh.loops])
				mesh.use_auto_smooth = True
			else:
				mesh.normals_split_custom_set([normals[l.vertex_index] for l in mesh.loops])
			mesh.update()

			# Assign weights (vertex groups)
			for joint_index in range(dna_reader.getJointCount()):
				vg_name = dna_reader.getJointName(joint_index)
				vg = obj.vertex_groups.new(name=vg_name)
				if joint_index in vertex_groups:
					_v, _w = vertex_groups[joint_index]
					for v, w in zip(_v, _w):
						vg.add([v], w, 'REPLACE')
			# Create basis shape key
			obj.shape_key_add(name='Basis')

			shape_targets = get_shape_keys_from_dna(dna_reader, mesh_index)
			for channel_name, shape_target in shape_targets.items():
				shape_key = obj.shape_key_add(name=f"{mesh_name}__{channel_name}")
				for layout_index, delta_tup in shape_target.items():
					delta = Vector(delta_tup)
					if delta.length > shape_key_threshold:
						shape_key.data[layout_index].co += delta

			# Create a UV layer if it doesn’t exist
			uv_layer = mesh.uv_layers.new(name="DiffuseUV")
			# Get the UV loop layer
			mesh.uv_layers.active = uv_layer

			_u = dna_reader.getVertexTextureCoordinateUs(mesh_index)
			_v = dna_reader.getVertexTextureCoordinateVs(mesh_index)
			uvs = []
			for layout_index in dna_reader.getVertexLayoutTextureCoordinateIndices(mesh_index):
				uv = (_u[layout_index], _v[layout_index])
				uvs.append(uv)
			

			# Check if the number of UVs matches the number of vertices
			if len(uvs) != len(mesh.vertices):
				raise ValueError("The number of UV coordinates doesn't match the number of vertices in the mesh!")

			# Iterate through polygons (faces) in the mesh
			for loop in mesh.loops:
				vertex_index = loop.vertex_index
				
				# Set the UV coordinates for this vertex
				uv_layer.data[loop.index].uv = uvs[vertex_index]

			mat = init_material(obj, mesh_shader_mapping.get(mesh_name, mesh_name))
			# Set viewport display properties
			mat.diffuse_color = (0.45, 0.45, 0.45, 1)
			mat.roughness = 0.45
			mat.metallic = 0.0
			lod_objects = objects.get(lod_index, None)
			if lod_objects is None:
				objects[lod_index] = lod_objects = list()
			lod_objects.append(obj)

			obj.rotation_euler.x = math.pi * 0.5
			if apply_transforms:
				bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
		return dict(sorted(objects.items()))
			
		
	def build_armature(
			dna_reader: 'dna.BinaryStreamReader',
			apply_transforms: bool = False,
			complete_skeleton: bool = False
	) -> None:
		# Reading armature

		# Create a new armature object
		bpy.ops.object.armature_add()
		armature = bpy.context.active_object
		armature.rotation_euler.x = math.pi * 0.5
		bpy.ops.object.mode_set(mode='EDIT')

		# Access the armature's edit bones
		edit_bones = armature.data.edit_bones
		bones = [bone for bone in edit_bones]
		for bone in bones:
			edit_bones.remove(bone)

		# Dictionary to store created bones for easy parent access
		created_bones = {}

		x_loc = dna_reader.getNeutralJointTranslationXs()
		y_loc = dna_reader.getNeutralJointTranslationYs()
		z_loc = dna_reader.getNeutralJointTranslationZs()
		x_rot = dna_reader.getNeutralJointRotationXs()
		y_rot = dna_reader.getNeutralJointRotationYs()
		z_rot = dna_reader.getNeutralJointRotationZs()
		
		for i in range(dna_reader.getJointCount()):
			joint_name = dna_reader.getJointName(i)
			location = [x_loc[i], y_loc[i], z_loc[i]]
			rotation = [x_rot[i], y_rot[i], z_rot[i]]
			rotation = [math.radians(a) for a in rotation]
			rotation = Euler(rotation, 'XYZ')

			# Create a new edit bone
			bone = edit_bones.new(joint_name)

			# Set the bone head location
			if i == 0:  # No parent, in object space
				bone.length = 1.0  # Set the bone length (ensuring it's not zero)
				# Combining translation and rotation into a transformation matrix
				bone.matrix = Matrix.Translation(location) @ rotation.to_matrix().to_4x4()
			else:
				parent_index = dna_reader.getJointParentIndex(i)
				parent_bone = created_bones[parent_index]
				bone.parent = parent_bone
				bone.length = 1.0  # Set the bone length (ensuring it's not zero)
				# Converting local coordinates and rotation angles to a transformation matrix
				local_matrix = Matrix.Translation(location) @ rotation.to_matrix().to_4x4()
				# Combining with the parent bone's transformation matrix
				global_matrix = parent_bone.matrix @ local_matrix
				# Setting the bone's position, rotation, and scale based on the global transformation matrix
				bone.matrix = global_matrix

			# Store the created bone for future reference
			created_bones[i] = bone
		if apply_transforms:
			for bone in edit_bones:
				bone.matrix = armature.matrix_local @ bone.matrix
			armature.matrix_local = Matrix.Identity(4)

		
		if complete_skeleton:
			bones = [
				("spine_03", "spine_04"),
				("spine_02", "spine_03"),
				("spine_01", "spine_02"),
				("pelvis", "spine_01")
			]
			for parent_name, bone_name in bones:
				bone = edit_bones[bone_name]
				parent = edit_bones.get(parent_name)
				if parent is None:
					parent = edit_bones.new(name=parent_name)

				parent.head = Vector([0.0, 0.0, 0.0])
				parent.tail = Vector([1.0, 0.0, 0.0])
				if bone.parent is not parent:
					bone.parent = parent
		bpy.ops.object.mode_set(mode="OBJECT")
		return armature

	"""
	def mesh_to_dna(calibrated: "dna.BinaryStreamReader") -> None:
		commands = dnacalib.CommandSequence()
		
		for mesh_index in range(calibrated.getMeshCount()):
			
			mesh_name = calibrated.getMeshName(mesh_index)
			if "lod0" not in mesh_name:
				continue
			obj = bpy.context.scene.objects[mesh_name]
			mesh = obj.data
			mesh: bpy.types.Mesh
			delta_xs, delta_ys, delta_zs = [], [], []
			old_xs = calibrated.getVertexPositionXs(mesh_index)
			old_ys = calibrated.getVertexPositionYs(mesh_index)
			old_zs = calibrated.getVertexPositionZs(mesh_index)
			mask = []
			vertex_indices = dict()
			for i, vertex_index in enumerate(calibrated.getVertexLayoutPositionIndices(mesh_index)):
				vertex_indices[vertex_index] = i

			
			for i in range(calibrated.getVertexPositionCount(mesh_index)):
				vertex_index = vertex_indices.get(i, None)
				if vertex_index is None:
					# Append deltas
					delta_xs.append(0.0)
					delta_ys.append(0.0)   
					delta_zs.append(0.0)
					mask.append(0.0)
				else:
					# Append deltas
					delta_xs.append(mesh.vertices[vertex_index].co.x)
					delta_ys.append(mesh.vertices[vertex_index].co.y)   
					delta_zs.append(mesh.vertices[vertex_index].co.z)
					mask.append(1.0)

			commands.add(
				dnacalib.SetVertexPositionsCommand(
					mesh_index,
					delta_xs,
					delta_ys,
					delta_zs,
					mask,
					dnacalib.VectorOperation_Interpolate
				)
			) 
			
		print("Running command sequence...")
		# Modifies calibrated DNA in-place
		commands.run(calibrated)
   
		@classmethod
		def status(cls, context) -> Tuple[bool, str]:
			dna_path = context.scene.meta_reforge_config.absolute_dna_path
			# Check if the file exists
			if not os.path.exists(dna_path):
				return False, "Invalid path"
			_, ext = os.path.splitext(dna_path)
			if ext.lower() != ".dna":
				return False, "Invalid extention"
			return True, "OK"
		
		def execute(self, context):
			dna_path = context.scene.meta_reforge_config.absolute_dna_path
			read_dna(dna_path)
			return {'FINISHED'}
	"""


else:
	build_armature = None
	build_meshes = None
