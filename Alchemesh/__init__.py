# --------------------------------------------------
# Copyright (C) 2024  CD Legasse
# --------------------------------------------------

bl_info = {
	"name": "AlcheMesh",
	"blender": (4, 1, 0),
	"category": "Object",
	"author": "CD Legasse",
	"description": "Retargets armatures and objects from a source mesh to target mesh using Radial Basis Functions.",
	"support": "COMMUNITY",
	"version": (1, 0, 0),
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
}

import bpy
import blf
import bgl
import types
from bpy.types import Panel, Operator
from bpy.props import BoolProperty
from bpy.app.handlers import persistent
import bpy.utils.previews
import bpy.app.timers
import numpy as np
import os, shutil
import sys
import subprocess
import importlib
import imp
import bmesh
import textwrap
import matplotlib.pyplot as plt
from collections import namedtuple
from mathutils import Vector
from sys import platform
from . import metahuman_tools as meta

current_dir = os.path.dirname(os.path.abspath(__file__))

preview_collections = {}

import bpy.utils.previews
pcoll = bpy.utils.previews.new()

my_icons_dir = os.path.join(os.path.dirname(__file__), "gfx")

pcoll.load("my_logoL", os.path.join(my_icons_dir, "logoL.png"), 'IMAGE')
pcoll.load("my_logoR", os.path.join(my_icons_dir, "logoR.png"), 'IMAGE')

preview_collections["main"] = pcoll

def import_module(module_name, global_name=None, reload=True, package=None):
	"""
	Import a module.
	:param module_name: Module to import.
	:param global_name: (Optional) Name under which the module is imported. If None the module_name will be used.
	:raises: ImportError and ModuleNotFoundError
	"""
	if global_name is None:
		global_name = module_name

	if global_name in globals():
		importlib.reload(globals()[global_name])
	else:
		globals()[global_name] = importlib.import_module(module_name,package)

def install_pip():
	"""
	Installs pip if not already present.
	"""
	try:
		subprocess.run([sys.executable, "-m", "pip", "--version"], check=True)
	except subprocess.CalledProcessError:
		import ensurepip
		ensurepip.bootstrap()
		os.environ.pop("PIP_REQ_TRACKER", None)

def install_and_import_module(module_name, package_name=None, global_name=None):
	"""
	Installs the package through pip and attempts to import the installed module.
	:param module_name: Module to import.
	:param package_name: (Optional) Name of the package that needs to be installed.
	:param global_name: (Optional) Name under which the module is imported.
	:raises: subprocess.CalledProcessError and ImportError
	"""
	if package_name is None:
		package_name = module_name

	if global_name is None:
		global_name = module_name

	environ_copy = dict(os.environ)
	environ_copy["PYTHONNOUSERSITE"] = "1"

	subprocess.run([sys.executable, "-m", "pip", "install", package_name], check=True, env=environ_copy)

	import_module(module_name, global_name)

def build_and_install_package(package_name, env, target_dir):
		"""Builds and installs a Python package from the current directory."""
		
		# subprocess.run([sys.executable, "pip", "install", "build<0.10.0"], check=True, env)
		subprocess.run([sys.executable, "-m", "pip", "install", "build<0.10.0"], check=True, env=env)

		# Build the package
		subprocess.run([sys.executable, "-m", "build"], check=True, env=env)
		
		# subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "build"], check=True, env=environ_copy)

		# Install the package
		# subprocess.run([sys.executable, "-m", "pip", "install", package_name], check=True, env=env)
			
		temp_dir = os.path.join(target_dir, 'temp_install_dir')

		# Install the package to the temporary directory
		subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name, '--target', temp_dir])

		# Find the package directory in the temporary directory
		package_dir = None
		for item in os.listdir(temp_dir):
			item_path = os.path.join(temp_dir, item)
			if os.path.isdir(item_path) and item != '__pycache__':
				package_dir = item_path
				break

		# Move the package directory to the target directory
		if package_dir:
			shutil.move(package_dir, os.path.join(target_dir, package_name))

		# Remove the temporary directory
		shutil.rmtree(temp_dir)

def clone_and_import_module(module_name, package_name=None, global_name=None, github_url=None):
	"""
	Installs the package through pip and attempts to import the installed module.
	:param module_name: Module to import.
	:param package_name: (Optional) Name of the package that needs to be installed.
	:param global_name: (Optional) Name under which the module is imported.
	:raises: subprocess.CalledProcessError and ImportError
	"""
	if package_name is None:
		package_name = module_name

	if global_name is None:
		global_name = module_name

	environ_copy = dict(os.environ)
	environ_copy["PYTHONNOUSERSITE"] = "1"

	# Locate Blender's Python executable
	blender_python = sys.executable

	# Clone the repo if necessary
	if not os.path.exists("PyGeM/setup.py"):
		print("Cloning repo")
		git.Git("PyGeM").clone(github_url)

	print("Starting PyGeM setup")

	os.chdir("PyGeM")

	# Install the package using Blender's Python executable
	subprocess.check_call([blender_python, "-m", "pip", "install", "."], env=environ_copy)

	os.chdir("..")

	# Import the module
	spec = importlib.util.find_spec(module_name)
	if spec is None:
		raise ImportError(f"Module {module_name} not found after installation")

	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	globals()[global_name] = module

def update_progress(job_title, progress):
	""" Update the progress bar in the console """
	length = 60  # Length of the progress bar
	block = int(round(length * progress))
	msg = "\r{0}: [{1}] {2}%".format(job_title, "#" * block + "-" * (length - block), round(progress * 100, 2))
	if progress >= 1:
		msg += " DONE\r\n"
	sys.stdout.write(msg)
	sys.stdout.flush()

def create_rbf_parameters_file(src_obj, dest_obj, rbf_type, filename):
	""" Create RBF parameters file from source and target meshes """
	original_control_points = []
	deformed_control_points = []
	
	proxy_level = bpy.context.scene.ALCHEMESH_settings.proxy_level
	
	# Collect control points based on the proxy level
	for i, v in enumerate(src_obj.data.vertices):
		if i % proxy_level == 0:  # Skip vertices based on proxy level
			original_control_points.append(v.co)
			deformed_control_points.append(dest_obj.data.vertices[i].co)
	
	original_cp_str = "\n						 ".join(" ".join(f"{coord:.3f}" for coord in vert) for vert in original_control_points)
	deformed_cp_str = "\n						 ".join(" ".join(f"{coord:.3f}" for coord in vert) for vert in deformed_control_points)
	
	rbf_params = f"""[Radial Basis Functions]
basis function: {rbf_type}
radius: 0.5

[Control points]
original control points: {original_cp_str}
deformed control points: {deformed_cp_str}
"""
	
	with open(filename, 'w') as file:
		file.write(rbf_params)
	
	print(f"RBF parameters file saved as {filename}")

def create_bone_mesh_from_armature(armature):
	# Select the armature object
	bpy.context.view_layer.objects.active = armature

	# Create a new mesh
	mesh = bpy.data.meshes.new("BoneMesh")
	new_object = bpy.data.objects.new("BoneMeshObject", mesh)

	# Link the new object to the current scene
	bpy.context.collection.objects.link(new_object)

	# Create a bmesh to build the mesh
	bm = bmesh.new()

	# Iterate over each bone in the armature
	for bone in armature.data.bones:
		# Get the world position of the bone's head and tail
		head = (armature.matrix_world @ bone.head_local)
		tail = (armature.matrix_world @ bone.tail_local)

		# Create two vertices for the head and tail of the bone
		head_vert = bm.verts.new(head)
		tail_vert = bm.verts.new(tail)

		# Create an edge between the head and tail vertices
		bm.edges.new((head_vert, tail_vert))

	# Update the mesh with the bmesh data
	bm.to_mesh(mesh)
	bm.free()

	return convert_bone_mesh_to_rbf_format(mesh)
	
def convert_bone_mesh_to_rbf_format(bone_mesh):
	"""
	Convert a bone mesh into a format readable by the RBF function.
	:param bone_mesh: The mesh object containing the bone vertices
	:return: A numpy array in the format readable by the RBF function
	"""
	# Extract the coordinates from the bone mesh
	x = np.array([v.co.x for v in bone_mesh.vertices])
	y = np.array([v.co.y for v in bone_mesh.vertices])
	z = np.array([v.co.z for v in bone_mesh.vertices])
	
	# Flatten the arrays and combine them
	mesh = np.array([x.ravel(), y.ravel(), z.ravel()])
		
	return mesh.T
	
def get_bone_positions_as_flat_array(armature):
	bone_positions = []

	bpy.context.view_layer.objects.active = armature
	bpy.ops.object.mode_set(mode='OBJECT')

	for bone in armature.pose.bones:
		head = armature.matrix_world @ bone.head
		tail = armature.matrix_world @ bone.tail
		
		bone_positions.extend([head.x, head.y, head.z, tail.x, tail.y, tail.z])

	return np.array(bone_positions)

def create_bone_positions_mesh(armature_obj, chunk_size):
	chunks = []
	bone_positions = []
	
	for bone in armature_obj.pose.bones:
		head = armature_obj.matrix_world @ bone.head
		tail = armature_obj.matrix_world @ bone.tail
		
		bone_positions.append([head.x, head.y, head.z])
		bone_positions.append([tail.x, tail.y, tail.z])
		
		if len(bone_positions) >= chunk_size:
			chunks.append(np.array(bone_positions))
			bone_positions = []

	if bone_positions:
		chunks.append(np.array(bone_positions))

	np.set_printoptions(threshold=sys.maxsize)
	
	return chunks
	
def rbf_armature(armature_obj, chunk_size):

	# Import PyGeM within the function
	from PyGeM import pygem
	from pygem import RBF
	
	rbf = RBF()
	rbf.read_parameters(filename='rbf_parameters.txt')
	
	bone_positions = []
	deformed_bones = []
	
	numBones = len(armature_obj.pose.bones)

	for i, bone in enumerate(armature_obj.pose.bones):
		head = armature_obj.matrix_world @ bone.head
		tail = armature_obj.matrix_world @ bone.tail

		# Append head and tail positions
		bone_positions.append([head.x, head.y, head.z])
		bone_positions.append([tail.x, tail.y, tail.z])

		# Process in chunks
		if len(bone_positions) >= chunk_size:
			# Run RBF on the current chunk and append the result
			deformed_chunk = rbf(np.array(bone_positions))
			deformed_bones.append(deformed_chunk)
			bone_positions = []
		update_progress("Morphing Bones",i/numBones)

	# Process any remaining positions
	if bone_positions:
		deformed_chunk = rbf(np.array(bone_positions))
		deformed_bones.append(deformed_chunk)

	# Flatten the deformed_bones list
	deformed_bones = np.concatenate(deformed_bones).flatten()

	np.set_printoptions(threshold=sys.maxsize)

	return deformed_bones

def rbf_mesh(mesh_obj, chunk_size):
	# Import PyGeM within the function
	from PyGeM import pygem
	from pygem import RBF
	
	rbf = RBF()
	rbf.read_parameters(filename='rbf_parameters.txt')
	
	vertex_positions = []
	deformed_vertices = []
	
	num_vertices = len(mesh_obj.data.vertices)

	for i, vertex in enumerate(mesh_obj.data.vertices):
		world_pos = mesh_obj.matrix_world @ vertex.co
		vertex_positions.append([world_pos.x, world_pos.y, world_pos.z])

		# Process in chunks
		if len(vertex_positions) >= chunk_size:
			deformed_chunk = rbf(np.array(vertex_positions))
			deformed_vertices.append(deformed_chunk)
			vertex_positions = []
		update_progress("Morphing Vertices", i / num_vertices)

	# Process any remaining positions
	if vertex_positions:
		deformed_chunk = rbf(np.array(vertex_positions))
		deformed_vertices.append(deformed_chunk)

	deformed_vertices = np.concatenate(deformed_vertices).flatten()
	
	return deformed_vertices

def update_mesh_vertex_positions_from_array(mesh_obj, deformed_mesh):
	# Ensure the deformed_mesh is reshaped properly
	deformed_mesh = deformed_mesh.reshape(-1, 3)
	
	# Enter edit mode to modify vertices
	bpy.context.view_layer.objects.active = mesh_obj
	bpy.ops.object.mode_set(mode='EDIT')
	
	bm = bmesh.from_edit_mesh(mesh_obj.data)
	
	for i, vertex in enumerate(bm.verts):
		new_pos = deformed_mesh[i]
		new_pos_vec = Vector((new_pos[0], new_pos[1], new_pos[2]))
		vertex.co = mesh_obj.matrix_world.inverted() @ new_pos_vec
	
	bmesh.update_edit_mesh(mesh_obj.data)
	
	# Exit edit mode
	bpy.ops.object.mode_set(mode='OBJECT')

def update_bone_positions_from_array(armature, deformed_mesh):
	# Ensure the deformed_mesh is reshaped properly
	deformed_mesh = deformed_mesh.reshape(-1, 3)
	
	# Enter edit mode to modify bones
	bpy.context.view_layer.objects.active = armature
	bpy.ops.object.mode_set(mode='EDIT')
	
	for i, bone in enumerate(armature.data.edit_bones):
		head_idx = 2 * i
		tail_idx = head_idx + 1
		
		head = deformed_mesh[head_idx]
		tail = deformed_mesh[tail_idx]

		# Convert numpy arrays to Blender vectors
		head_vec = Vector((head[0], head[1], head[2]))
		tail_vec = Vector((tail[0], tail[1], tail[2]))

		# Apply the new positions
		bone.head = armature.matrix_world.inverted() @ head_vec
		bone.tail = armature.matrix_world.inverted() @ tail_vec
	
	# Exit edit mode
	bpy.ops.object.mode_set(mode='OBJECT')

def create_retargeted_armature(src_obj, dest_obj, rbf_type):
	"""Create a retargeted armature based on source and target meshes"""
	
	# Import PyGeM within the function
	from PyGeM import pygem
	from pygem import RBF

	scene = bpy.context.scene
	create_rbf_parameters_file(src_obj, dest_obj, rbf_type, "rbf_parameters.txt")

	# Iterate over the list of objects
	for item in scene.deform_objects:
		if item.object is None:
			continue

		obj = item.object
		
		if obj.type == 'ARMATURE':
			armature_obj = obj

			bpy.ops.object.select_all(action='DESELECT')
			armature_obj.select_set(True)
			bpy.context.view_layer.objects.active = armature_obj

			deformed_bones = rbf_armature(armature_obj, chunk_size=100)
			
			original_target_location = dest_obj.location.copy()
			
			src_armature_matrix_world = armature_obj.matrix_world.copy()
			src_mesh_matrix_world = src_obj.matrix_world.copy()
			relative_transform = src_armature_matrix_world.inverted() @ src_mesh_matrix_world
			dest_obj.location = relative_transform.to_translation()
			bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
			
			if False:#scene.auto_rig_retarget_overwrite_original:
				retargeted_armature = armature_obj
				dest_obj.name = src_obj.name

				# Parent dest_obj to retargeted_armature
				bpy.ops.object.select_all(action='DESELECT')
				dest_obj.select_set(True)
				retargeted_armature.select_set(True)
				bpy.context.view_layer.objects.active = retargeted_armature
				bpy.ops.object.parent_set(type='OBJECT')

				update_bone_positions_from_array(retargeted_armature, deformed_bones)
				
				bpy.ops.object.select_all(action='DESELECT')
			else:
				bpy.ops.object.duplicate()
				retargeted_armature = bpy.context.view_layer.objects.active
				retargeted_armature.name = armature_obj.name + "_retarg"

				# Parent dest_obj to retargeted_armature
				bpy.ops.object.select_all(action='DESELECT')
				dest_obj.select_set(True)
				retargeted_armature.select_set(True)
				bpy.context.view_layer.objects.active = retargeted_armature
				bpy.ops.object.parent_set(type='OBJECT')

				update_bone_positions_from_array(retargeted_armature, deformed_bones)
		
				retargeted_armature.location = original_target_location
				
				bpy.ops.object.select_all(action='DESELECT')

			arm_mod = None
			for mod in dest_obj.modifiers:
				if mod.type == 'ARMATURE':
					arm_mod = mod
					break

			if arm_mod is None:
				arm_mod = dest_obj.modifiers.new(name="Armature", type='ARMATURE')
			
			arm_mod.object = retargeted_armature
			arm_mod.use_vertex_groups = True
			
		elif obj.type == 'MESH':
			# Duplicate the mesh for retargeting
			bpy.ops.object.select_all(action='DESELECT')
			obj.select_set(True)
			bpy.context.view_layer.objects.active = obj
			bpy.ops.object.duplicate()
			duplicated_mesh = bpy.context.view_layer.objects.active
			duplicated_mesh.name = obj.name + "_retarg"

			# Apply RBF deformation to the duplicated mesh
			deformed_vertices = rbf_mesh(duplicated_mesh, chunk_size=5)
			update_mesh_vertex_positions_from_array(duplicated_mesh, deformed_vertices)

			# Calculate the relative position transformation
			original_target_location = dest_obj.location
			relative_position = obj.location - src_obj.location
			duplicated_mesh.location = dest_obj.location + relative_position

class OBJECT_OT_auto_rig_retarget(bpy.types.Operator):
	bl_idname = "object.auto_rig_retarget"
	bl_label = "Process"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		scene = context.scene
		src_obj = scene.auto_rig_retarget_src
		dest_obj = scene.auto_rig_retarget_dest
		rbf_type = scene.auto_rig_retarget_rbf
		morphing = True

		create_retargeted_armature(src_obj, dest_obj, rbf_type)

		morphing = False
		
		return {'FINISHED'}

def _label_multiline(context, text, parent):
	chars = int(context.region.width / 7)	# 7 pix on 1 character
	wrapper = textwrap.TextWrapper(width=chars)
	text_lines = wrapper.wrap(text=text)
	for text_line in text_lines:
		parent.label(text=text_line)
		
class OBJECT_OT_test_dna(bpy.types.Operator):
	bl_idname = "object.test_dna"
	bl_label = "Test DNA"
	bl_description = "Test DNA Files"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		scene = context.scene
		source_dna = scene.auto_rig_retarget_source_dna
		output_dna = scene.auto_rig_retarget_output_dna
		
		meta.create_json_dna(source_dna, output_dna)
		
		return {'FINISHED'}

# Custom draw callback
def draw_scaled_icon(img, x, y, width, height):
	
	# Bind the texture
	bgl.glEnable(bgl.GL_BLEND)
	bgl.glBindTexture(bgl.GL_TEXTURE_2D, img.bindcode)
	
	# Draw the scaled icon
	bgl.glBegin(bgl.GL_QUADS)
	bgl.glTexCoord2f(0, 0)
	bgl.glVertex2f(x, y)
	bgl.glTexCoord2f(1, 0)
	bgl.glVertex2f(x + width, y)
	bgl.glTexCoord2f(1, 1)
	bgl.glVertex2f(x + width, y + height)
	bgl.glTexCoord2f(0, 1)
	bgl.glVertex2f(x, y + height)
	bgl.glEnd()
	
	# Unbind the texture
	bgl.glBindTexture(bgl.GL_TEXTURE_2D, 0)
	bgl.glDisable(bgl.GL_BLEND)
	
class OBJECT_PT_auto_rig_retarget_panel(bpy.types.Panel):
	bl_label = "AlcheMesh"
	bl_idname = "OBJECT_PT_auto_rig_retarget"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = 'AlcheMesh'
	bl_icon = 'LINK_BLEND'
	

	def draw(self, context):
		
		layout = self.layout
		scene = context.scene

						
		row = layout.row()
		row.label(text="╔════════════════════════════════════════════════════════════════════════════════════════╗")
				
		for index, tab in enumerate(scene.alchemesh_tabs):
			tab.draw(layout, context)
			row = layout.row()	
			
		row.label(text="╚════════════════════════════════════════════════════════════════════════════════════════╝")
		row = layout.row()

class ALCHEMESH_Settings(bpy.types.PropertyGroup):
	proxy_level: bpy.props.IntProperty(
		name="Proxy Level",
		default=1,
		min=1,
		description="Sets the level of proxy for control points, higher values is lower lod level, and less accurate. Lower numbers are more accurate, but at a cost of generation time."
	)

class ALCHEMESH_OT_install_dependencies(bpy.types.Operator):
	bl_idname = "example.install_dependencies"
	bl_label = "Install Python Dependencies"
	bl_description = ("Downloads and installs the required Setuptools, GitPython, and PyGeM packages for this add-on. "
					  "Internet connection is required. Blender may have to be started with "
					  "elevated permissions in order to install the package")
	bl_options = {"REGISTER", "INTERNAL"}

	@classmethod
	def poll(self, context):
		return not dependencies_installed

	def execute(self, context):
		try:
			print("Checking Pip Installation")
			install_pip()
			print("Cycling through dependencies")
			install_and_import_module(module_name="setuptools",
									  package_name=None,
									  global_name=None)
			install_and_import_module(module_name="git",
									  package_name="GitPython",
									  global_name=None)
			clone_and_import_module(module_name="PyGeM",
									  package_name="pygem",
									  global_name=None,
									  github_url="https://github.com/mathLab/PyGeM")
		except (subprocess.CalledProcessError, ImportError) as err:
			self.report({"ERROR"}, str(err))
			return {"CANCELLED"}
		
		
		global dependencies_installed
		dependencies_installed = True

		return {"FINISHED"}

class ALCHEMESH_preferences(bpy.types.AddonPreferences):
	bl_idname = __name__

	def draw(self, context):
		layout = self.layout
		row = layout.row()
		
		my_logoL = preview_collections["main"]["my_logoL"]
		my_logoR = preview_collections["main"]["my_logoR"]
		
		split = row.split(factor=0.5)
		
		col_left = split.column()
		left_row = col_left.row(align=True)
		left_row.alignment = 'RIGHT'
		left_row.template_icon(icon_value=my_logoL.icon_id, scale=5)
		
		col_right = split.column()
		right_row = col_right.row(align=True)
		right_row.alignment = 'LEFT'
		right_row.template_icon(icon_value=my_logoR.icon_id, scale=5)
		
		box = layout.box()
		row = box.row()
		
		if dependencies_installed:
			row.label(text="PyGeM is installed.", icon='CHECKMARK')
			row.label(text="The addon is ready for use.", icon='INFO')
		else:
			row.label(text="PyGeM is not installed.", icon='ERROR')
			row.label(text="Press the button below to install the required dependencies.", icon='INFO')
			
			warning_box = box.box()
			warning_box.label(text="⚠️ Warning: To install PyGeM, Blender will follow these steps:")
			warning_box.label(text="1. Install SetupTools.")
			warning_box.label(text="2. Install GitPython.")
			warning_box.label(text="3. Clone the custom PyGeM repository.")
			warning_box.label(text="4. Build and import PyGeM into the Blender environment.")

			install_row = box.row()
			install_row.operator(ALCHEMESH_OT_install_dependencies.bl_idname, icon="CONSOLE")
			
		# Add the MetaHuman license agreement box
		license_box = layout.box()
		license_box.label(text="MetaHuman DNA Calibration License Agreement")
		
		if not bpy.context.scene.metahuman_dna_license_agreed:
			# license_box.label(text="To use MetaHuman Mode, you must agree to the MetaHuman DNA Calibration License Agreement.")
			text = 'To use MetaHuman Mode, you must agree to the MetaHuman DNA Calibration License Agreement.'
			_label_multiline(
				context=context,
				text=text,
				parent=license_box
			)
			
			# Display the license text or provide a link
			# You can either display the full license text directly or provide a link to an external document.
			# For simplicity, let's provide a link here.
			# license_box.label(text="Please read the license agreement at the following link:")
			row = license_box.row()
			text = 'Please read the license agreement at the following link:'
			_label_multiline(
				context=context,
				text=text,
				parent=license_box
			)
			
			# Create a row split into two columns
			row = license_box.row()
			split = row.split(factor=0.3)  # Adjust factor as needed for desired layout
			col1 = split.column()
			col2 = split.column()

			# Add the checkbox to the left column
			col1.prop(bpy.context.scene, "metahuman_dna_license_agreed", text="I agree")

			# Add the URL button to the right column
			col2.operator("wm.url_open", text="License Agreement").url = "https://raw.githubusercontent.com/EpicGames/MetaHuman-DNA-Calibration/main/LICENSE"
		else:
			license_box.label(text="You have agreed to the MetaHuman DNA Calibration License.", icon='CHECKMARK')

def p_filter(self, object):
	return object.type == 'MESH'

class DeformObjectItem(bpy.types.PropertyGroup):
	name: bpy.props.StringProperty(name="Object Name")
	object: bpy.props.PointerProperty(name="Object", type=bpy.types.Object)
	progress: bpy.props.FloatProperty(name="Progress", default=0.0, min=0.0, max=1.0)

bpy.utils.register_class(DeformObjectItem)

class UL_DeformObjects(bpy.types.UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
		row = layout.row(align=True)
		row.prop(item, "object", text="", emboss=False, icon='OBJECT_DATA')
		progress = item.progress
		if progress is not None and morphing:
			row.progress(factor = progress, type = 'BAR')


bpy.utils.register_class(UL_DeformObjects)

class SCENE_OT_add_deform_object(bpy.types.Operator):
	bl_idname = "scene.add_deform_object"
	bl_label = "Add Deform Object"

	def execute(self, context):
		scene = context.scene
		item = scene.deform_objects.add()
		selected_object = context.active_object
		if selected_object:
			item.object = selected_object
		else:
			item.object = None
		scene.deform_objects_index = len(scene.deform_objects) - 1
		return {'FINISHED'}

class SCENE_OT_remove_deform_object(bpy.types.Operator):
	bl_idname = "scene.remove_deform_object"
	bl_label = "Remove Deform Object"

	def execute(self, context):
		scene = context.scene
		index = scene.deform_objects_index

		scene.deform_objects.remove(index)
		if index > 0:
			scene.deform_objects_index -= 1

		return {'FINISHED'}

class OBJECT_OT_rebind_armature(bpy.types.Operator):
	bl_idname = "object.rebind_armature"
	bl_label = "Rebind Armature"
	bl_description = "Rebind the armature with updated neutral positions"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		scene = context.scene
		source_dna = scene.auto_rig_retarget_source_dna
		output_dna = scene.auto_rig_retarget_output_dna
		morphed_armature = scene.auto_rig_retarget_morphed_armature

		meta.rebind_armature(source_dna,output_dna,morphed_armature)

		return {'FINISHED'}
		
class OBJECT_OT_transfer_weights(bpy.types.Operator):
	bl_idname = "object.transfer_weights"
	bl_label = "Transfer Vertex Groups"
	bl_description = "Transfer Vertex Groups from the source mesh to the target mesh."
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		scene = context.scene
		src_obj = scene.auto_rig_retarget_src
		dest_obj = scene.auto_rig_retarget_dest
		
		for src_vgroup in src_obj.vertex_groups:
			v_group_name = src_vgroup.name
			if not v_group_name not in dest_obj.vertex_groups:
				vg = dest_obj.vertex_groups.get(v_group_name)
				if vg is not None:
					dest_obj.vertex_groups.remove(vg)
			if v_group_name not in dest_obj.vertex_groups:
				dest_obj.vertex_groups.new(name=v_group_name)

		num_vertices = len(src_obj.data.vertices)
		for i, src_vert in enumerate(src_obj.data.vertices):
			update_progress("Transferring Bone Weights", i / num_vertices)
			
			src_weights = {group.group: group.weight for group in src_vert.groups}
			
			for group_index, weight in src_weights.items():
				v_group_name = src_obj.vertex_groups[group_index].name
				if v_group_name in dest_obj.vertex_groups:
					v_group_target = dest_obj.vertex_groups[v_group_name]
					v_group_target.add([src_vert.index], weight, 'REPLACE')
		return {'FINISHED'}
		
class OBJECT_OT_transfer_shapekeys(bpy.types.Operator):
	bl_idname = "object.transfer_shapekeys"
	bl_label = "Transfer Shape Keys"
	bl_description = "Transfer Shape Keys from the source mesh to the target mesh."
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		scene = context.scene
		src_obj = scene.auto_rig_retarget_src
		dest_obj = scene.auto_rig_retarget_dest
		if src_obj.data.shape_keys:
			for sk in src_obj.data.shape_keys.key_blocks:
				if sk.name != "Basis":
					if sk.name in dest_obj.data.shape_keys.key_blocks:
						dest_sk = dest_obj.data.shape_keys.key_blocks[sk.name]
					else:
						dest_sk = dest_obj.shape_key_add(name=sk.name)
					for i, coord in enumerate(sk.data):
						dest_sk.data[i].co = coord.co
		return {'FINISHED'}
		
bpy.utils.register_class(SCENE_OT_add_deform_object)
bpy.utils.register_class(SCENE_OT_remove_deform_object)

class CustomTab(bpy.types.PropertyGroup):
	expand: bpy.props.BoolProperty(name="Expand", default=False)
	icon: bpy.props.StringProperty(name="Icon", default="WORLD")
	tab_type: bpy.props.StringProperty()
	
	def draw(self, layout, context):
		box = layout.box()
		row = box.row()
		row = box.row()
		row.prop(self, "expand", icon='TRIA_RIGHT' if not self.expand else 'TRIA_DOWN', text="", emboss=False)
		row.label(text=f"{self.name}")
		row.operator("wm.call_menu", text="", icon=self.icon)
		row = box.row()

		if self.expand:
			self.draw_custom_ui(box, context)
	
	def draw_custom_ui(self, layout, context):
		draw_custom_ui_dispatcher(self, layout, context)

class AddCustomTabOperator(bpy.types.Operator):
	bl_idname = "scene.add_custom_tab"
	bl_label = "Add Custom Tab"
	
	def execute(self, context):
		scene = context.scene
		new_tab = scene.alchemesh_tabs.add()
		new_tab.name = f"Tab {len(scene.alchemesh_tabs)}"
		new_tab.icon = "WORLD"
		return {'FINISHED'}

# Define the draw methods for each specific tab
def draw_general_settings_ui(self, layout, context):
	scene = context.scene
	row = layout.row()
	box = row.box()
	# row = box.row()
	# row.prop(scene, "auto_rig_retarget_rbf", text="RBF:")
		
	# row = box.row()
	# row.alignment = 'RIGHT'
	# row.label(text="Overwrite Original:")
	# row.prop(scene, "auto_rig_retarget_overwrite_original", text="")

	# row = box.row()
	# row.alignment = 'RIGHT'
	# row.label(text="Transfer Weights:")
	# row.prop(scene, "auto_rig_retarget_transfer_weights", text="")

	# row = box.row()
	# row.alignment = 'RIGHT'
	# row.label(text="Transfer Shape Keys:")
	# row.prop(scene, "auto_rig_retarget_transfer_shape_keys", text="")

	settings = context.scene.ALCHEMESH_settings

def draw_mesh_inputs_ui(self, layout, context):
	scene = context.scene
	row = layout.row()
	box = row.box()
	col = box.column()
	
	col.prop_search(scene, "auto_rig_retarget_src", bpy.data, "objects", text="Source")
	col.prop_search(scene, "auto_rig_retarget_dest", bpy.data, "objects", text="Target")
	
def draw_deform_ui(self, layout, context):
	scene = context.scene
	row = layout.row()
	box = row.box()
	row = box.row()
	
	row.label(text="Deform Batch:")
	box.template_list("UL_DeformObjects", "", scene, "deform_objects", scene, "deform_objects_index")

	row = box.row(align=True)
	row.operator("scene.add_deform_object", icon='ADD', text="")
	row.operator("scene.remove_deform_object", icon='REMOVE', text="")
	row = layout.row()

	row.label(text="Proxy Level:")
	settings = context.scene.ALCHEMESH_settings
	row.prop(settings, "proxy_level", text="")
	row = layout.row()
	
	row.prop(scene, "auto_rig_retarget_rbf", text="RBF:")
	row = layout.row()
	if (dependencies_installed == False):
		row.label(text="Python Depencencies Missing!", icon="ERROR")
		row = layout.row()
		box = row.box()
		text = 'Please open the AlcheMesh Addon Preferences to install the required dependencies.'
		_label_multiline(
			context=context,
			text=text,
			parent=box
		)
	else:
		row.operator("object.auto_rig_retarget")

def draw_data_transfer_ui(self, layout, context):
	scene = context.scene
	layout.label(text="Transfer from Source Mesh:")
	row = layout.row();
	row.operator("object.transfer_weights", text="Vertex Groups")
	row = layout.row();
	row.operator("object.transfer_shapekeys", text="Shape Keys")

def draw_metahuman_dna_ui(self, layout, context):
	scene = context.scene
	if scene.metahuman_dna_license_agreed:
		row = layout.row()
		box = row.box()
		row = box.row()
		row.prop(scene, "auto_rig_retarget_source_dna", text="Input")
		row = box.row()
		row.prop(scene, "auto_rig_retarget_output_dna", text="Output")
		
		row = box.row()
		row.enabled = bool(scene.auto_rig_retarget_source_dna) and bool(scene.auto_rig_retarget_output_dna)
		row.operator("object.test_dna", text="Test DNA")

		row = box.row()
		row.prop(scene, "auto_rig_retarget_morphed_armature", text="Morphed Armature")
		row = box.row()
		row.operator("object.rebind_armature", text="Rebind Armature")

		# Import MetaHuman Section
		row = layout.row()
		box = row.box()
		row = box.row()
		row.prop(scene, "import_metahuman", text="Import MetaHuman")
		
		if scene.import_metahuman:
			row = box.row()
			row.prop(scene, "body_fbx_path", text="Body FBX")
			
			row = box.row()
			row.enabled = bool(scene.body_fbx_path) and bool(scene.auto_rig_retarget_source_dna)
			row.operator("object.import_metahuman", text="Import MetaHuman")
			
			row = box.row()
			metahuman_face_model_present = any("mhf_" in obj.name.lower() for obj in bpy.data.objects)
			row.enabled = bool(scene.auto_rig_retarget_source_dna) and metahuman_face_model_present
			row.operator("object.import_face_rig", text="Import Face Rig")
	else:
		row = layout.row()
		box = row.box()
		row = box.row()
		row.label(text="MetaHuman License Error!", icon="ERROR")
		row = layout.row()
		box = row.box()
		text = 'Please open the AlcheMesh Addon Preferences and agree to the MetaHuman DNA Calibration License.'
		_label_multiline(
			context=context,
			text=text,
			parent=box
		)

# Dispatcher function to call the appropriate draw method based on tab type
def draw_custom_ui_dispatcher(self, layout, context):
	if self.tab_type == "GeneralSettings":
		draw_general_settings_ui(self, layout, context)
	elif self.tab_type == "MeshInputs":
		draw_mesh_inputs_ui(self, layout, context)
	elif self.tab_type == "DeformUI":
		draw_deform_ui(self, layout, context)
	elif self.tab_type == "DataTransfer":
		draw_data_transfer_ui(self, layout, context)
	elif self.tab_type == "MetaHumanDNA":
		draw_metahuman_dna_ui(self, layout, context)

# Function to ensure initial tabs are added
def ensure_initial_tab(scene):
	print("Attempting to add tabs")
	if len(scene.alchemesh_tabs) == 0:
		print("Tabs are adding")

		# List of tabs with their names, icons, and types
		tabs_info = [
			# ("General Settings", "TOOL_SETTINGS", "GeneralSettings"),
			("Mesh Inputs", "MESH_DATA", "MeshInputs"),
			("Deformation", "MOD_SIMPLEDEFORM", "DeformUI"),
			("Data Transfer", "GROUP_VERTEX", "DataTransfer"),
			("MetaHuman DNA", "RNA", "MetaHumanDNA")
		]
		
		for tab_name, tab_icon, tab_type in tabs_info:
			tab = scene.alchemesh_tabs.add()
			tab.name = tab_name
			tab.icon = tab_icon
			tab.tab_type = tab_type
	else:
		print("Tabs are not empty")

# Persistent handler to call ensure_initial_tab after registration
@persistent
def load_handler(dummy):
	ensure_initial_tab(bpy.context.scene)
	
def deferred_initial_tab():
	icon_image = bpy.data.images.load(os.path.join(my_icons_dir, "logo.png"))
	ensure_initial_tab(bpy.context.scene)
	return None

class OBJECT_OT_import_metahuman(bpy.types.Operator):
	bl_idname = "object.import_metahuman"
	bl_label = "Import MetaHuman"
	bl_description = "Import MetaHuman from selected FBX file"
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):
		# TODO: Implement the import functionality here
		self.report({'INFO'}, "Import MetaHuman functionality not implemented yet.")
		return {'FINISHED'}

class OBJECT_OT_import_face_rig(bpy.types.Operator):
	bl_idname = "object.import_face_rig"
	bl_label = "Import Face Rig"
	bl_description = "Import Face Rig for MetaHuman"
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):
		# TODO: Implement the import functionality here
		self.report({'INFO'}, "Import Face Rig functionality not implemented yet.")
		return {'FINISHED'}

def register():
	
	global morphing
	morphing = False
	global dependencies_installed
	dependencies_installed = False
	global icon_image
	icon_image = 0
		
	# bpy.types.Scene.auto_rig_retarget_overwrite_original = bpy.props.BoolProperty(
		# name="Overwrite Original",
		# description="Delete the original source model and armature, and replace them with the destination model and new armature",
		# default=False
	# )
	# bpy.types.Scene.auto_rig_retarget_transfer_weights = bpy.props.BoolProperty(
		# name="Transfer Weights",
		# description="Set the values of the vertex weights in the target mesh to match that of the source mesh",
		# default=False
	# )
	# bpy.types.Scene.auto_rig_retarget_transfer_shape_keys = bpy.props.BoolProperty(
		# name="Transfer Shape Keys",
		# description="Copy all of the shape keys other than default from the source mesh to the target mesh",
		# default=False
	# )
	bpy.types.Scene.auto_rig_retarget_metahuman_mode = bpy.props.BoolProperty(
		name="MetaHuman Mode",
		description="Enable MetaHuman Mode for retargeting",
		default=False
	)
	bpy.types.Scene.auto_rig_retarget_source_dna = bpy.props.StringProperty(
		name="Input DNA",
		description="Path to the input DNA file",
		subtype='FILE_PATH'
	)
	bpy.types.Scene.auto_rig_retarget_morphed_armature= bpy.props.PointerProperty(
		name="Morphed Armature", type=bpy.types.Object)
	bpy.types.Scene.auto_rig_retarget_output_dna = bpy.props.StringProperty(
		name="DNA Output",
		description="Path to save the DNA output file",
		subtype='FILE_PATH'
	)
	bpy.types.Scene.metahuman_dna_license_agreed = bpy.props.BoolProperty(
		name="Agree to MetaHuman DNA Calibration License",
		description="Agree to the MetaHuman DNA Calibration License to use MetaHuman Mode",
		default=False
	)
	bpy.types.Scene.auto_rig_retarget_rbf = bpy.props.EnumProperty(
		name="RBF Type",
		description="Choose the RBF type",
		items=[
			('gaussian_spline', 'Gaussian Spline', ''),
			('multi_quadratic_biharmonic_spline', 'Multi-Quadratic Biharmonic Spline', ''),
			('inv_multi_quadratic_biharmonic_spline', 'Inv Multi-Quadratic Biharmonic Spline', ''),
			('thin_plate_spline', 'Thin Plate Spline', ''),
			('polyharmonic_spline', 'Polyharmonic Spline', '')
		],
		default='polyharmonic_spline'
	)
	bpy.types.Scene.my_pointer = bpy.props.PointerProperty(
		type=bpy.types.Object,
		poll=p_filter,
	)
	bpy.types.Scene.body_fbx_path = bpy.props.StringProperty(
		name="Body FBX Path",
		description="Path to the body FBX file",
		subtype='FILE_PATH'
	)
	bpy.types.Scene.import_metahuman = bpy.props.BoolProperty(
		name="Import MetaHuman",
		description="Enable to import MetaHuman"
	)
			
	bpy.utils.register_class(OBJECT_OT_import_metahuman)
	bpy.utils.register_class(OBJECT_OT_import_face_rig)
	bpy.types.Scene.deform_objects = bpy.props.CollectionProperty(type=DeformObjectItem)
	bpy.types.Scene.deform_objects_index = bpy.props.IntProperty(name="Deform Objects Index", default=0)
	bpy.utils.register_class(OBJECT_OT_transfer_weights)
	bpy.utils.register_class(OBJECT_OT_transfer_shapekeys)
	bpy.utils.register_class(OBJECT_OT_rebind_armature)
	bpy.utils.register_class(OBJECT_OT_auto_rig_retarget)
	bpy.utils.register_class(OBJECT_OT_test_dna)
	bpy.utils.register_class(OBJECT_PT_auto_rig_retarget_panel)
	bpy.utils.register_class(ALCHEMESH_Settings)
	bpy.types.Scene.ALCHEMESH_settings = bpy.props.PointerProperty(type=ALCHEMESH_Settings)
	bpy.types.Scene.auto_rig_retarget_src = bpy.props.PointerProperty(type=bpy.types.Mesh)
	bpy.types.Scene.auto_rig_retarget_dest = bpy.props.PointerProperty(type=bpy.types.Mesh)
	bpy.utils.register_class(ALCHEMESH_OT_install_dependencies)
	bpy.utils.register_class(ALCHEMESH_preferences)
	bpy.types.Scene.progress_value = bpy.props.FloatProperty(name="Progress", default=0.0, min=0.0, max=1.0)
	bpy.types.Scene.is_progressing = bpy.props.BoolProperty(name="Is Progressing", default=False)
	
	try:
		imp.find_module('PyGeM')
		dependencies_installed = True
	except ImportError:
		dependencies_installed = False
	
	bpy.utils.register_class(CustomTab)
	bpy.utils.register_class(AddCustomTabOperator)
	bpy.types.Scene.alchemesh_tabs = bpy.props.CollectionProperty(type=CustomTab)
	
	bpy.app.timers.register(deferred_initial_tab)
	
	bpy.app.handlers.load_post.append(load_handler)
	
def unregister():
	meta.unload_dll()

	global custom_icons
	bpy.utils.previews.remove(custom_icons)
	
	bpy.utils.unregister_class(OBJECT_OT_import_metahuman)
	bpy.utils.unregister_class(OBJECT_OT_import_face_rig)
	bpy.utils.unregister_class(OBJECT_OT_transfer_weights)
	bpy.utils.unregister_class(OBJECT_OT_transfer_shapekeys)
	bpy.utils.unregister_class(OBJECT_OT_test_dna)
	bpy.utils.unregister_class(OBJECT_OT_rebind_armature)
	bpy.utils.unregister_class(OBJECT_OT_auto_rig_retarget)
	bpy.utils.unregister_class(OBJECT_PT_auto_rig_retarget_panel)
	bpy.utils.unregister_class(ALCHEMESH_OT_install_dependencies)
	bpy.utils.unregister_class(ALCHEMESH_Settings)
	bpy.utils.unregister_class(CustomTab)
	bpy.utils.unregister_class(AddCustomTabOperator)

	bpy.app.handlers.load_post.remove(initialize_tabs)
	# bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update_post_handler)
	
	del bpy.types.Scene.alchemesh_tabs
	del bpy.types.Scene.auto_rig_retarget_source_dna
	del bpy.types.Scene.auto_rig_retarget_output_dna
	del bpy.types.Scene.auto_rig_retarget_morphed_armature
	# del bpy.types.Scene.auto_rig_retarget_overwrite_original
	del bpy.types.Scene.auto_rig_retarget_transfer_weights
	del bpy.types.Scene.auto_rig_retarget_transfer_shape_keys
	del bpy.types.Scene.auto_rig_retarget_metahuman_mode
	del bpy.types.Scene.auto_rig_retarget_source_dna
	del bpy.types.Scene.auto_rig_retarget_output_dna
	del bpy.types.Scene.metahuman_dna_license_agreed
	del bpy.types.Scene.auto_rig_retarget_src
	del bpy.types.Scene.auto_rig_retarget_dest
	del bpy.types.Scene.progress_value
	del bpy.types.Scene.is_progressing
	del bpy.types.Scene.auto_rig_retarget_rbf

if __name__ == "__main__":
	register()
