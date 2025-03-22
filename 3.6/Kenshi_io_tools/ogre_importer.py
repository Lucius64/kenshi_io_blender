
import os
from statistics import mean
import traceback
from typing import List, Dict, Set

import bpy
import bmesh
from bpy.types import (
    Context,
    Mesh,
    Object,
    Operator,
    )
from mathutils import Matrix, Vector
import numpy as np

from .util import func_timer
from .kenshi_blender_tool import *


def set_bone_head_position(bones: List[BoneData]):
    for key in bones:
        thisbone = key
        head_position = Vector3(key.position.x, key.position.y, key.position.z)

        while len(thisbone.parent_name) != 0:
            parentbone = [b for b in bones if b.name == thisbone.parent_name]
            if len(parentbone) == 0:
                break
            angle, axis = parentbone[0].rotate.to_angle_axis()
            ppos = parentbone[0].position
            protmat = Matrix.Rotation(angle.valueRadians(),
                                      3,
                                      Vector([axis.x, axis.y, axis.z])
                                      ).inverted()

            new_head_position =  protmat.transposed() @ Vector([head_position.x,
                                                                head_position.y,
                                                                head_position.z])
            position = Vector3(ppos.x + new_head_position[0],
                                ppos.y + new_head_position[1],
                                ppos.z + new_head_position[2])
            head_position = position
            thisbone = parentbone[0]

        key.position_head_as = head_position


def set_bone_rotation(context: Context, bones: List[BoneData]):
    scene_collection = context.scene.collection
    scene_layer = context.view_layer
    data_objects = bpy.data.objects

    object_map: Dict[str, Object] = {}
    for bone in bones:
        obj = data_objects.new(bone.name, None)
        object_map[bone.name] = obj
        scene_collection.objects.link(obj)

    for bone in bones:
        if bone.parent_name != '':
            obj = object_map.get(bone.name)
            Parent = object_map.get(bone.parent_name)
            obj.parent = Parent

    for bone in bones:
        obj = object_map.get(bone.name)
        angle, axis = bone.rotate.to_angle_axis()
        loc = bone.position
        euler = Matrix.Rotation(angle.valueRadians(),
                                3,
                                Vector([axis.x, -axis.z, axis.y])
                                ).to_euler()
        obj.location = [loc.x, -loc.z, loc.y]
        obj.rotation_euler = [euler[0], euler[1], euler[2]]

    scene_layer.update()

    for bone in bones:
        obj = object_map.get(bone.name)
        _, rot, _ = obj.matrix_world.decompose()
        rotmatAS = rot.to_matrix()
        bone.rotate_matrix_as = rotmatAS

    for bone in bones:
        obj = object_map.get(bone.name)
        scene_collection.objects.unlink(obj)
        data_objects.remove(obj)

    scene_layer.update()


def create_skeleton(
        context: Context,
        import_info_log: List[str],
        skeleton_data: SkeletonData,
        skeleton_name: str):
    bones = skeleton_data.get_bones(has_helper=True)

    set_bone_head_position(bones=bones)
    set_bone_rotation(context=context, bones=bones)

    scene_collection = context.scene.collection
    scene_layer = context.view_layer

    armature = bpy.data.armatures.new(skeleton_name)
    rig = bpy.data.objects.new(skeleton_name, armature)
    rig.show_in_front = True
    scene_collection.objects.link(rig)
    scene_layer.objects.active = rig
    scene_layer.update()

    averageBone = mean([bone.position.x for bone in bones])
    if averageBone == 0:
        averageBone = 0.2

    print('Default bone length:', averageBone)
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in bones:
        boneName = bone.name
        children = bone.child_names
        bone_obj = armature.edit_bones.new(boneName)
        bone_obj['OGREID'] = bone.id
        headPos = bone.position_head_as
        tailVector = 0
        if len(children) > 0:
            for child in children:
                b = [bone.position.x for bone in bones if bone.name == child]
                tailVector = max(tailVector, b[0])

        if tailVector == 0:
            tailVector = averageBone

        rotmat: Matrix = bone.rotate_matrix_as
        tmpR = Matrix(((0, 1, 0), (1, 0, 0), (0, 0, 1))) @ rotmat.transposed()
        boneRotMatrix = Matrix((tmpR.col[0], tmpR.col[1], tmpR.col[2]))

        bone_obj.head = Vector([0, 0, 0])
        bone_obj.tail = Vector([0, tailVector, 0])
        bone_obj.transform(boneRotMatrix)
        bone_obj.translate(Vector([headPos.x, -headPos.z, headPos.y]))

    for bone in bones:
        parent_bone = [b for b in bones if b.name == bone.parent_name]
        if len(parent_bone) != 0:
            bone_obj = armature.edit_bones[bone.name]
            bone_obj.parent = armature.edit_bones[parent_bone[0].name]

    bone_map: Dict[int, str] = {}
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in armature.bones.keys():
        if bone.startswith('Helper'):
            context.object.data.edit_bones.remove(armature.edit_bones[bone])

    for bone in armature.edit_bones:
            if 'OGREID' in bone:
                bone_map[int(bone['OGREID'])] = bone.name
                import_info_log.append(f"Created bone {bone['OGREID']} {bone.name}")

    bpy.ops.object.mode_set(mode='OBJECT')
    return rig, bone_map


def create_mesh(
        context: Context,
        import_info_log: List[str],
        mesh_data: MeshData,
        armature: Object,
        bone_map: Dict[str, str],
        mesh_name: str,
        import_normals: bool = True,
        import_shapekeys: bool = True,
        create_materials: bool = True,
        use_filename: bool = False,
        select_encoding='utf-8',
        cleanup_vertices: str = 'DEFAULT',
        submesh_name_delimiter: str = '',
        ):
    mesh_objects: List[Object] = []
    scene_collection = context.scene.collection
    scene_layer = context.view_layer

    submeshes = mesh_data.get_submeshes()
    submesh_count = len(str(len(submeshes)))

    for submesh in submeshes:
        submesh_index = submesh.index
        submesh_name = (f'{mesh_name}{submesh_name_delimiter}{submesh_index:0{submesh_count}}'
                        if use_filename
                        else submesh.encorded_name.decode(select_encoding,
                                                          errors='replace'))

        material_name = (submesh.encorded_material.decode(select_encoding,
                                                          errors='replace')
                         if create_materials
                         else '')

        me = bpy.data.meshes.new(submesh_name)
        ob = bpy.data.objects.new(submesh_name, me)
        scene_collection.objects.link(ob)
        scene_layer.objects.active = ob
        scene_layer.update()

        verts = submesh.get_positions()
        faces = submesh.faces

        me.vertices.add(submesh.geometry.vertex_count)
        me.loops.add(submesh.face_count * 3)
        me.polygons.add(submesh.face_count)
        me.vertices.foreach_set('co', verts)
        me.loops.foreach_set('vertex_index', faces)
        me.polygons.foreach_set('loop_start', [i * 3 for i in range(submesh.face_count)])
        me.polygons.foreach_set('use_smooth', [True] * submesh.face_count)

        if create_materials:
            material_index = bpy.data.materials.find(material_name)
            material = (bpy.data.materials.new(name=material_name)
                        if material_index == -1
                        else bpy.data.materials[material_index])
            me.materials.append(material=material)

        if submesh.geometry.has_texture_coord:
            nd_texcoords = submesh.get_texcoords()
            for texcorrd_index in range(nd_texcoords.shape[0]):
                uv_layer = me.attributes.new(name=f'UVLayer{texcorrd_index}',
                                             type='FLOAT2',
                                             domain='CORNER'
                                             )
                uv_layer.data.foreach_set('vector', nd_texcoords[texcorrd_index])

        if submesh.geometry.has_colors:
            nd_colors, nd_alphas = submesh.get_colors()
            color_data = me.attributes.new(name=f'Colour{submesh_index}',
                                           type='BYTE_COLOR',
                                           domain='CORNER'
                                           )
            color_data.data.foreach_set('color_srgb', nd_colors)
            alpha_data = me.attributes.new(name=f'Alpha{submesh_index}',
                                           type='BYTE_COLOR',
                                           domain='CORNER'
                                           )
            alpha_data.data.foreach_set('color_srgb', nd_alphas)

        if bone_map:
            submesh.set_bone_mapping(bone_map)
            for vg in submesh.get_vertex_groups():
                grp = ob.vertex_groups.new(name=vg.name)
                for v, w in vg.group:
                    grp.add(v, w, 'REPLACE')

        if armature:
            mod = ob.modifiers.new('OgreSkeleton', 'ARMATURE')
            mod.object = bpy.data.objects[armature.name]
            mod.use_bone_envelopes = False
            mod.use_vertex_groups = True

        if import_shapekeys:
            shape_keys = submesh.get_shapekeys()
            shape_key_add = ob.shape_key_add
            if len(shape_keys) > 0:
                shape_key_add(name='Basis')
                for name, pose in shape_keys:
                    if name.startswith('fake_pose'):
                        continue
                    import_info_log.append(f'Created pose {name}')
                    shape_key_add(name=name)
                    me.shape_keys.key_blocks[name].data.foreach_set('co', pose.ravel())

        me.update(calc_edges=True)
        if hasattr(me, 'use_auto_smooth'):
            me.use_auto_smooth = True

        if cleanup_vertices == 'KEEP_FACE':
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(me)
            face_dict: Dict[Vector, int] = {}
            dupulicate_faces: List[int] = []

            bm.faces.ensure_lookup_table()
            for face in me.polygons:
                v = Vector(
                    (
                        round(face.center.x, 2),
                        round(face.center.y, 2),
                        round(face.center.z, 2)
                    )
                ).freeze()

                i = face_dict.get(v, -1)
                if i < 0:
                    face_dict[v] = face.index
                    bm.faces[face.index].select = True
                else:
                    dupulicate_faces.append(face.index)
                    bm.faces[face.index].select = False

            bmesh.update_edit_mesh(me)
            bpy.ops.mesh.remove_doubles(threshold=0.0001)
            if len(dupulicate_faces) > 0:
                bpy.ops.mesh.select_all(action = 'INVERT')
                bpy.ops.mesh.remove_doubles(threshold=0.0001)
            bm.free()
            bpy.ops.mesh.select_all(action = 'SELECT')
            bpy.ops.object.mode_set(mode='OBJECT')

        elif cleanup_vertices == 'DEFAULT':
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.remove_doubles(threshold=0.0001)
            bpy.ops.object.mode_set(mode='OBJECT')

        if import_normals and submesh.geometry.has_normals:
            normals = submesh.get_normals()

            noChange = len(me.loops) == (submesh.face_count * 3)
            if noChange:
                me.normals_split_custom_set(normals)
            else:
                print('Removed',
                      submesh.face_count - len(me.loops) / 3,
                      'faces')
                vertices = verts.reshape(-1, 3).tolist()
                face_array = [faces[i:i + 3] for i in range(0, submesh.face_count * 3, 3)]
                split = []
                split_append = split.append
                polyIndex = 0
                for face in face_array:
                    if match_face(face, vertices, me, polyIndex):
                        polyIndex += 1
                        for vx in face:
                            split_append(normals[vx])

                if len(split) == len(me.loops):
                    me.normals_split_custom_set(split)
                else:
                    print('Warning: Failed to import mesh normals',
                          polyIndex,
                          '/',
                          len(me.polygons))
        import_info_log.append(f'Created mesh {submesh_name}')
        ob.select_set(False)
        mesh_objects.append(ob)

    if armature:
        for mesh_object in mesh_objects:
            print('Move to', armature.location)
            mesh_object.location = armature.location
            mesh_object.rotation_euler = armature.rotation_euler
            mesh_object.rotation_axis_angle = armature.rotation_axis_angle
            mesh_object.rotation_quaternion = armature.rotation_quaternion

    for mesh_object in mesh_objects:
        mesh_object.select_set(True)


def match_face(
        face: List[int],
        vertices: List[int],
        mesh: Mesh,
        index: int) -> bool:
    if index >= len(mesh.polygons):
        return False

    loop = mesh.polygons[index].loop_start
    for v in face:
        vi = mesh.loops[loop].vertex_index
        vx = mesh.vertices[vi].co
        if (vx - Vector(vertices[v])).length_squared > 1e-6:
            return False
        loop += 1
    return True


def create_animation(
        animations: List[AnimationData],
        import_info_log: List[str],
        armature: Object,
        fps: float = 24.0,
        round_frames: bool = False):
    if len(animations) > 0:
        armature.animation_data_create()
        pose_bones = armature.pose.bones
        mat: Dict[str, Matrix3] = {}
        fix1 = Matrix([(1, 0, 0), (0, 0, 1), (0, -1, 0)])
        fix2 = Matrix([(0, 1, 0), (0, 0, 1), (1, 0, 0)])
        for bone in pose_bones:
            m = (fix2 @ bone.parent.matrix.to_3x3().transposed() @ bone.matrix.to_3x3()).transposed() if bone.parent else (fix1 @  bone.matrix.to_3x3()).transposed()
            mat[bone.name] = Matrix3([
                [m[0][0], m[0][1], m[0][2]],
                [m[1][0], m[1][1], m[1][2]],
                [m[2][0], m[2][1], m[2][2]]
                ])

        actions_new = bpy.data.actions.new
        tracks_new = armature.animation_data.nla_tracks.new
        for animation in animations:
            action = actions_new(animation.name)
            import_info_log.append(f'Created action {action.name}')

            frame_end = int(animation.length * fps + 0.5)

            fcurves_new = action.fcurves.new
            for track_data in animation.get_animations(bone_matrix_map=mat, fps=fps, round_frame=round_frames):
                bone = pose_bones[track_data.name]
                if not bone:
                    continue

                bone.rotation_mode = 'QUATERNION'

                nd_locations = track_data.nd_locations
                length = int(nd_locations.shape[1] / 2)
                for i in range(nd_locations.shape[0]):
                    curve = fcurves_new(bone.path_from_id('location'),
                                        index=i,
                                        action_group=bone.name)
                    curve.keyframe_points.add(length)
                    curve.keyframe_points.foreach_set("co", nd_locations[i])
                    curve.update()
                    if not round_frames:
                        curve.bake(0, frame_end, remove='ALL')

                nd_rotations = track_data.nd_rotations
                # length = nd_rotations.shape[1] / 2
                for i in range(nd_rotations.shape[0]):
                    curve = fcurves_new(bone.path_from_id('rotation_quaternion'),
                                        index=i,
                                        action_group=bone.name)
                    curve.keyframe_points.add(length)
                    curve.keyframe_points.foreach_set("co", nd_rotations[i])
                    curve.update()
                    if not round_frames:
                        curve.bake(0, frame_end, remove='ALL')

                if track_data.has_scale:
                    nd_scales = track_data.nd_scales
                    # length = nd_scales.shape[1] / 2
                    for i in range(nd_scales.shape[0]):
                        curve = fcurves_new(bone.path_from_id('scale'),
                                            index=i,
                                            action_group=bone.name)
                        curve.keyframe_points.add(length)
                        curve.keyframe_points.foreach_set("co", nd_scales[i])
                        curve.update()
                    if not round_frames:
                        curve.bake(0, frame_end, remove='ALL')

            track = tracks_new()
            track.name = animation.name
            track.mute = True
            track.strips.new(animation.name, 0, action)


@func_timer
def load(operator: Operator,
         context: Context,
         filepath: str,
         import_normals: bool = True,
         import_shapekeys: bool = True,
         import_animations: bool = False,
         round_frames: bool = False,
         use_selected_skeleton: bool = False,
         create_materials: bool = True,
         use_filename: bool = False,
         select_encoding: str = 'utf-8',
         cleanup_vertices: str = 'DEFAULT',
         submesh_name_delimiter: str = '',
         ) -> Set[str]:
    if not os.path.isfile(filepath):
        operator.report({'WARNING'}, 'Selected file is not exist')
        return {'CANCELLED'}

    print('loading', filepath)

    if not filepath.lower().endswith('.mesh'):
        return {'CANCELLED'}

    try:
        import_info_log = []

        folder, mesh_file = os.path.split(filepath)
        log_file = os.path.join(os.path.dirname(os.path.realpath( __file__ )),
                                'log',
                                'kenshi_io_OGRE.log')
        serializer = KenshiObjectSerializer(logfile=log_file)
        serializer.add_resource_location(folder)
        mesh_data = serializer.load_mesh(mesh_file)

        selected_skeleton = context.active_object if use_selected_skeleton and context.active_object and context.active_object.type == 'ARMATURE' else None
        objs = context.selected_objects
        for obj in objs:
            if obj.type == 'MESH':
                obj.select_set(False)

        skeleton_data = None
        bone_map: Dict[int, str] = {}
        if selected_skeleton:
            for bone in selected_skeleton.data.bones:
                if 'OGREID' in bone:
                    bone_map[int(bone['OGREID'])] = bone.name

            if not bone_map:
                operator.report({'WARNING'}, 'Selected armature has no OGRE data')
        else:
            skeleton_filename = mesh_data.get_linked_skeleton_name()
            if len(skeleton_filename) != 0:
                skeleton_data = mesh_data.get_linked_skeleton()
                if skeleton_data:
                    skeleton_name = os.path.splitext(skeleton_filename)[0]

                    selected_skeleton, bone_map = create_skeleton(context=context,
                                                                  import_info_log=import_info_log,
                                                                  skeleton_data=skeleton_data,
                                                                  skeleton_name=skeleton_name)
                else:
                    operator.report({'WARNING'}, 'Failed to load linked skeleton')

        create_mesh(context=context,
                    import_info_log=import_info_log,
                    mesh_data=mesh_data,
                    armature=selected_skeleton,
                    bone_map=bone_map,
                    mesh_name=os.path.splitext(mesh_file)[0],
                    import_normals=import_normals,
                    import_shapekeys=import_shapekeys,
                    select_encoding=select_encoding,
                    create_materials=create_materials,
                    use_filename=use_filename,
                    cleanup_vertices=cleanup_vertices,
                    submesh_name_delimiter=submesh_name_delimiter,
                    )

        if import_animations and skeleton_data:
            render = context.scene.render
            if round_frames:
                fps = int(round(skeleton_data.calc_animation_fps()))
                print('Setting FPS to', fps)
                render.fps = fps
            create_animation(animations=skeleton_data.get_animations(),
                             import_info_log=import_info_log,
                             armature=selected_skeleton,
                             fps=render.fps,
                             round_frames=round_frames)

        for obj in objs:
            if obj.type == 'MESH':
                obj.select_set(True)

        print('\n'.join(import_info_log))
        print('done.')
        operator.report({'INFO'}, 'Import successful')

    except:
        err_mes = traceback.format_exc()
        print(err_mes)
        operator.report({'ERROR'}, f'Import error!\n{err_mes}')

    return {'FINISHED'}


@func_timer
def load_skeleton(operator: Operator,
                  context: Context,
                  filepath: str,
                  import_animations: bool = False,
                  round_frames: bool = False,
                  use_selected_skeleton: bool = False) -> Set[str]:
    if not os.path.isfile(filepath):
        operator.report({'WARNING'}, 'Selected file is not exist')
        return {'CANCELLED'}

    print('loading', filepath)

    if not filepath.lower().endswith('.skeleton'):
        return {'CANCELLED'}

    selected_skeleton = context.active_object if use_selected_skeleton and context.active_object and context.active_object.type == 'ARMATURE' else None
    if selected_skeleton and not import_animations:
        operator.report({'WARNING'}, "Canceled because 'use selected armature' A is enabled and 'Import animation' is disabled")
        return {'CANCELLED'}

    try:
        import_info_log = []

        folder, skeleton_filename = os.path.split(filepath)
        log_file = os.path.join(os.path.dirname(os.path.realpath( __file__ )),
                                'log',
                                'kenshi_io_OGRE.log')
        serializer = KenshiObjectSerializer(logfile=log_file)
        serializer.add_resource_location(folder)
        skeleton_data = serializer.load_skeleton(filepath)

        if not selected_skeleton:
            skeleton_name = os.path.splitext(skeleton_filename)[0]
            selected_skeleton, _ = create_skeleton(context=context,
                                                   import_info_log=import_info_log,
                                                   skeleton_data=skeleton_data,
                                                   skeleton_name=skeleton_name)

        if import_animations:
            render = context.scene.render
            if round_frames:
                fps = int(round(skeleton_data.calc_animation_fps()))
                print('Setting FPS to', fps)
                render.fps = fps
            create_animation(animations=skeleton_data.get_animations(),
                             import_info_log=import_info_log,
                             armature=selected_skeleton,
                             fps=render.fps,
                             round_frames=round_frames)

        selected_skeleton.select_set(True)

        print('\n'.join(import_info_log))
        print('done.')
        operator.report({'INFO'}, 'Import successful')

    except:
        err_mes = traceback.format_exc()
        print(err_mes)
        operator.report({'ERROR'}, f'Import error!\n{err_mes}')

    return {'FINISHED'}
