
import os
import sys
from math import radians
import traceback
from typing import List, Dict, Tuple, Set

import numpy as np
import bpy
import bmesh
from mathutils import Vector, Matrix, Quaternion

from .util import func_timer
sys.path.append(os.path.dirname(__file__))
from Kenshi_blender_tool import *


@func_timer
def set_animations(
        context: bpy.types.Context, 
        export_info_log: List[str],
        skeleton_data: SkeletonData,
        armature: bpy.types.Object,
        is_visual_keying: bool = False,
        use_scale_keyframe: bool = False):
    bones = skeleton_data.get_bones(has_helper=False)
    if len(bones) == 0:
        return

    scene_layer = context.view_layer
    animdata = armature.animation_data
    if animdata:
        actions: Set[bpy.types.Action] = set()
        if animdata.nla_tracks:
            actions = {strip.action for track in animdata.nla_tracks.values() for strip in track.strips.values() if strip.action}

        currentAction = animdata.action
        if currentAction:
            actions.add(currentAction)

        hidden = armature.hide_viewport
        armature.hide_viewport = False
        prev = scene_layer.objects.active
        scene_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        target_pose_bones = {}

        fix1 = Matrix([
            (1, 0, 0),
            (0, 0, 1),
            (0, -1, 0)
            ])
        fix2 = Matrix([
            (0, 1, 0),
            (0, 0, 1),
            (1, 0, 0)
            ])
        fix_matrix = {}
        bone_path_map: Dict[str, Tuple[str, str, str]] = {}
        p_bones = armature.pose.bones
        e_bones = armature.data.edit_bones
        for bone in bones:
            p_bone = p_bones[bone.name]
            bone_path_map[bone.name] = (p_bone.path_from_id('location'),
                                        p_bone.path_from_id('rotation_quaternion'),
                                        p_bone.path_from_id('scale'))
            e_bone = e_bones[bone.name]
            m = fix2 @ e_bone.parent.matrix.to_3x3().transposed() @ e_bone.matrix.to_3x3() if e_bone.parent else fix1 @  e_bone.matrix.to_3x3()
            fix_matrix[bone.name] = Matrix3([
                [m[0][0], m[0][1], m[0][2]],
                [m[1][0], m[1][1], m[1][2]],
                [m[2][0], m[2][1], m[2][2]]
                ])
            target_pose_bones[bone.name] = p_bone

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        scene_layer.objects.active = prev
        armature.hide_viewport = hidden

        fps = context.scene.render.fps
        frame_step = context.scene.frame_step

        if is_visual_keying:
            new_scene = context.blend_data.scenes.new('bake_work')
            new_scene_layer = new_scene.view_layers[0]
            new_scene.collection.objects.link(armature)
            for bone in p_bones:
                for contraint in bone.constraints:
                    new_scene.collection.objects.link(contraint.target)

            new_scene.render.fps = fps
            context.scene.frame_step = frame_step

        for act in sorted(actions, key=lambda action: action.name):
            export_info_log.append('Export action {}'.format(act.name))
            start, end = act.frame_range
            animation = AnimationData()
            animation.name = act.name
            animation.length = (int(end) - int(start)) / fps
            if is_visual_keying:
                set_baked_track(scene=new_scene,
                                view_layer=new_scene_layer,
                                action=act,
                                animation=animation,
                                armature=armature,
                                pose_bones=target_pose_bones,
                                fix_matrix=fix_matrix,
                                frame_start=start,
                                frame_end=end,
                                step=frame_step,
                                fps=fps,
                                use_scale_keyframe=use_scale_keyframe)
            else:
                set_track(animation=animation,
                          fcurves=act.fcurves, 
                          bone_path_map=bone_path_map,
                          fix_matrix=fix_matrix,
                          frame_start=start,
                          frame_end=end,
                          step=frame_step,
                          fps=fps,
                          use_scale_keyframe=use_scale_keyframe)
            skeleton_data.add_animation(animation)

        if is_visual_keying:
            bone_conut = len(p_bones)
            p_bones.foreach_set('location', [0, 0, 0] * bone_conut)
            p_bones.foreach_set('rotation_quaternion', [1, 0, 0, 0] * bone_conut)
            p_bones.foreach_set('rotation_euler', [0, 0, 0] * bone_conut)
            p_bones.foreach_set('scale', [1, 1, 1] * bone_conut)
            animdata.action = currentAction
            context.blend_data.scenes.remove(new_scene)


def set_track(
        animation: AnimationData,
        fcurves: bpy.types.ActionFCurves,
        bone_path_map: Dict[str, Tuple[str, str, str]],
        fix_matrix: Dict[str, Matrix3],
        frame_start: float,
        frame_end: float,
        step: int = 1,
        fps: int = 24,
        use_scale_keyframe: bool = False):
    fcurves_find = fcurves.find
    start = int(frame_start)
    end = int(frame_end) + 1
    frame_size = end - start

    nd_array = np.arange(start, end, step, dtype=np.float32)
    nd_times = (nd_array - start) / fps
    nd_ones = np.ones(frame_size, dtype=np.float32)
    nd_zeros = np.zeros(frame_size, dtype=np.float32)
    for bone_name, path in bone_path_map.items():
        fc_loc_x, fc_loc_y, fc_loc_z = [fcurves_find(data_path=path[0], index=i) for i in range(3)]
        nd_loc_x = np.frompyfunc(fc_loc_x.evaluate, 1, 1)(nd_array) if fc_loc_x else nd_zeros
        nd_loc_y = np.frompyfunc(fc_loc_y.evaluate, 1, 1)(nd_array) if fc_loc_y else nd_zeros
        nd_loc_z = np.frompyfunc(fc_loc_z.evaluate, 1, 1)(nd_array) if fc_loc_z else nd_zeros

        fc_rot_w, fc_rot_x, fc_rot_y, fc_rot_z = [fcurves_find(data_path=path[1], index=i) for i in range(4)]
        nd_rot_w = np.frompyfunc(fc_rot_w.evaluate, 1, 1)(nd_array) if fc_rot_w else nd_ones
        nd_rot_x = np.frompyfunc(fc_rot_x.evaluate, 1, 1)(nd_array) if fc_rot_x else nd_zeros
        nd_rot_y = np.frompyfunc(fc_rot_y.evaluate, 1, 1)(nd_array) if fc_rot_y else nd_zeros
        nd_rot_z = np.frompyfunc(fc_rot_z.evaluate, 1, 1)(nd_array) if fc_rot_z else nd_zeros

        fc_scl_x, fc_scl_y, fc_scl_z = [fcurves_find(data_path=path[2], index=i) for i in range(3)]
        nd_scl_x = np.frompyfunc(fc_scl_x.evaluate, 1, 1)(nd_array) if fc_scl_x else nd_ones
        nd_scl_y = np.frompyfunc(fc_scl_y.evaluate, 1, 1)(nd_array) if fc_scl_y else nd_ones
        nd_scl_z = np.frompyfunc(fc_scl_z.evaluate, 1, 1)(nd_array) if fc_scl_z else nd_ones

        nd_locs = np.vstack([nd_loc_x, nd_loc_y, nd_loc_z])
        nd_rots = np.vstack([nd_rot_w, nd_rot_x, nd_rot_y, nd_rot_z])
        nd_scls = np.vstack([nd_scl_x, nd_scl_y, nd_scl_z])
        animation.append_animation_track(bone_name=bone_name,
                                         bone_matrix=fix_matrix[bone_name],
                                         nd_times=nd_times,
                                         nd_locations=nd_locs,
                                         nd_rotations=nd_rots,
                                         nd_scales=nd_scls,
                                         use_scale=use_scale_keyframe)


def set_baked_track(
        scene: bpy.types.Scene,
        view_layer: bpy.types.ViewLayer,
        action: bpy.types.Action,
        animation: AnimationData,
        armature: bpy.types.Object,
        pose_bones: Dict[str, bpy.types.PoseBone],
        fix_matrix: Dict[str, Matrix3],
        frame_start: float,
        frame_end: float,
        step: int = 1,
        fps: int = 24,
        use_scale_keyframe: bool = False):
    start = int(frame_start)
    end = int(frame_end) + 1
    pbones = armature.pose.bones
    bone_conut = len(pbones)
    pbones.foreach_set('location', [0, 0, 0] * bone_conut)
    pbones.foreach_set('rotation_quaternion', [1, 0, 0, 0] * bone_conut)
    pbones.foreach_set('rotation_euler', [0, 0, 0] * bone_conut)
    pbones.foreach_set('scale', [1, 1, 1] * bone_conut)
    armature.animation_data.action = action

    times: List[float] = []
    matrix_dict: Dict[str, List[List[float]]] = {name: [] for name in pose_bones.keys()}

    for frame in range(start, end, step):
        scene.frame_set(frame)
        view_layer.update()
        times.append((frame - start) / fps)
        for name, pbone in pose_bones.items():
            mat = armature.convert_space(pose_bone=pbone,
                                         matrix=pbone.matrix,
                                         from_space='POSE',
                                         to_space='LOCAL')
            matrix_dict[name].append([list(row) for row in mat])
    animation.set_animation_tracks(bone_matrix_map=fix_matrix,
                                   pose_matrix_map=matrix_dict,
                                   time_array=times,
                                   use_scale=use_scale_keyframe)


def set_mesh(
        context: bpy.types.Context,
        export_info_log: List[str],
        mesh_data: MeshData,
        selected_objects: List[bpy.types.Object],
        applyModifiers: bool = True,
        export_color: bool = False,
        tangent_format: str = 'TANGENT_4',
        export_poses: bool = False,
        optimize: bool = True):

    submesh_array: List[SubMeshData] = []
    for submesh_index, ob in enumerate(selected_objects):
        submesh = SubMeshData()
        submesh.index = submesh_index
        submesh.submesh_name = ob.name

        material_name = ob.name
        for m in ob.data.materials:
            if m:
                material_name = m.name
                break
        submesh.material = material_name

        temp_object = ob.evaluated_get(context.evaluated_depsgraph_get()) if applyModifiers else ob
        mesh = temp_object.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()

        if not mesh.uv_layers.active :
            tangent_format = 'TANGENT_0'

        if tangent_format != 'TANGENT_0':
            mesh.calc_tangents(uvmap = mesh.uv_layers.active.name)
        else:
            mesh.calc_normals_split()

        loop_count = len(mesh.loops)
        nd_vert_indices = np.empty(loop_count, dtype=np.int32)
        mesh.loops.foreach_get('vertex_index', nd_vert_indices)

        nd_loop_indices = np.empty(loop_count, dtype=np.int32)
        mesh.loops.foreach_get('index', nd_loop_indices)

        vertex_count = len(mesh.vertices)

        nd_positions = np.empty(vertex_count * 3, dtype=np.float32)
        mesh.vertices.foreach_get('co', nd_positions)

        nd_normals = np.empty(loop_count * 3, dtype=np.float32)
        mesh.loops.foreach_get('normal', nd_normals)

        uv_layer = mesh.uv_layers.active.data if mesh.uv_layers.active else None
        if uv_layer:
            nd_texcoords = np.empty(loop_count * 2, dtype=np.float32)
            uv_layer.foreach_get('uv', nd_texcoords)
        else:
            nd_texcoords = np.empty(2, dtype=np.float32)

        tangent_dimensions = 4 if tangent_format == 'TANGENT_4' else 3
        if tangent_format != 'TANGENT_0':
            nd_tangents = np.empty(loop_count * 3, dtype=np.float32)
            mesh.loops.foreach_get('tangent', nd_tangents)

            nd_bitangent_signs = np.empty(loop_count, dtype=np.float32)
            mesh.loops.foreach_get('bitangent_sign', nd_bitangent_signs)

            nd_bitangents = np.empty(loop_count * 3, dtype=np.float32)
            mesh.loops.foreach_get('bitangent', nd_bitangents)
        else:
            nd_tangents = np.empty(3, dtype=np.float32)
            nd_bitangent_signs = np.empty(1, dtype=np.float32)
            nd_bitangents = np.empty(3, dtype=np.float32)

        nd_colors = np.empty(4, dtype=np.float32)
        nd_alphas = np.empty(4, dtype=np.float32)
        if export_color and len(mesh.vertex_colors) > 0:
            vertex_colors = mesh.vertex_colors.items()
            for k, v in vertex_colors:
                if not k.lower().startswith('alpha'):
                    nd_colors = np.empty(loop_count * 4, dtype=np.float32)
                    v.data.foreach_get('color', nd_colors)
                    break
            for k, v in vertex_colors:
                if k.lower().startswith('alpha'):
                    nd_alphas = np.empty(loop_count * 4, dtype=np.float32)
                    v.data.foreach_get('color', nd_alphas)
                    break

        out_nd_indices = submesh.set_vertex(nd_vert_indices=nd_vert_indices,
                                            nd_loop_indices=nd_loop_indices,
                                            nd_positions=nd_positions.reshape(-1, 3),
                                            nd_normals=nd_normals.reshape(-1, 3),
                                            nd_tangents=nd_tangents.reshape(-1, 3),
                                            nd_bitangent_signs=nd_bitangent_signs,
                                            nd_bitangents=nd_bitangents.reshape(-1, 3),
                                            nd_texcoords=nd_texcoords.reshape(-1, 2),
                                            nd_colors=nd_colors.reshape(-1, 4),
                                            nd_alphas=nd_alphas.reshape(-1, 4),
                                            tangent_dimensions=tangent_dimensions,
                                            optimize=optimize)

        if export_poses and mesh.shape_keys and mesh.shape_keys.key_blocks:
            for shape_key in mesh.shape_keys.key_blocks:
                shape_key.name

                nd_works = np.empty(vertex_count * 3, dtype=np.float32)
                shape_key.data.foreach_get('co', nd_works)

                nd_works_r = np.empty(vertex_count * 3, dtype=np.float32)
                shape_key.relative_key.data.foreach_get('co', nd_works_r)
                nd_shape_keys = nd_works - nd_works_r
                if nd_shape_keys.sum() == 0:
                    continue

                nd_shape_keys = nd_shape_keys.reshape(vertex_count, 3)

                submesh.append_shapekey(shape_key.name, nd_shape_keys, out_nd_indices)

        bone_assignments = [BoneAssignmentData(vert.index,
                                               mesh_data.get_bone_id(ob.vertex_groups[group.group].name),
                                               group.weight)
                                               for vert in mesh.vertices
                                               for group in vert.groups]
        submesh.set_bone_assignments(bone_assignments, out_nd_indices)

        temp_object.to_mesh_clear()

        export_info_log.append('Export mesh {}'.format(ob.name))
        submesh_array.append(submesh)

    mesh_data.set_submeshes(submesh_array)


def set_bones(
        export_info_log: List[str],
        mesh_data: MeshData,
        skeleton_data: SkeletonData,
        armature: bpy.types.Object,
        export_all_bones: bool = False):

    bones: List[BoneData] = []
    if armature:
        data: bpy.types.Armature = armature.data

        rot = Matrix.Rotation(radians(-90), 4, 'X')    # Rotate to y-up coordinates
        fix = Matrix.Rotation(radians(90), 4, 'Z') @ Matrix.Rotation(radians(180), 4, 'X')    # Fix bone axis

        bone_id_max = max([bone['OGREID'] for bone in data.bones if 'OGREID' in bone])
        index = 0
        for bone in data.bones:
            if 'OGREID' in bone:
                id = bone['OGREID']
            else:
                if export_all_bones:
                    index += 1
                    id = bone_id_max + index
                else:
                    continue

            rest: Matrix = (bone.parent.matrix_local @ fix @ rot).inverted() @ bone.matrix_local @ fix @ rot if bone.parent else rot @ bone.matrix_local @ fix @ rot
            loc_x, loc_y, loc_z = rest.to_translation()
            rot_w, rot_x, rot_y, rot_z = rest.to_quaternion()

            old_bone = BoneData(id,
                                bone.name,
                                Vector3(loc_x, loc_y, loc_z),
                                OgreQuaternion(rot_w, rot_x, rot_y, rot_z),
                                Vector3(1, 1, 1),
                                bone.parent.name if bone.parent else '',
                                [])

            export_info_log.append('Export bone {} {}'.format(id, bone.name))
            bones.append(old_bone)

        if skeleton_data:
            skeleton_data.set_bones(bones)
        if mesh_data:
            mesh_data.set_bone_mapping(bones)
            mesh_data.set_linked_skeleton_name('{}.skeleton'.format(armature.name))


@func_timer
def save(
        operator: bpy.types.Operator,
        context: bpy.types.Context,
        filepath: str,
        tangent_format: str = 'TANGENT_4',
        export_colour: bool = False,
        apply_transform: bool = True,
        apply_modifiers: bool = True,
        export_skeleton: bool = False,
        export_poses: bool = False,
        export_animation: bool = False,
        export_all_bones: bool = False,
        mesh_optimize: bool = True,
        export_version: str = 'V_1_10',
        is_visual_keying: bool = False,
        use_scale_keyframe: bool = False):
    if export_version == 'V_1_8':
        mesh_version = MeshVersion.V_1_8
        skeleton_version = SkeletonVersion.V_Latest
    elif export_version == 'V_1_4':
        mesh_version = MeshVersion.V_1_4
        skeleton_version = SkeletonVersion.V_1_0
    else:
        mesh_version = MeshVersion.V_Latest
        skeleton_version = SkeletonVersion.V_Latest

    if not filepath.lower().endswith('.mesh'):
        filepath = "{}.mesh".format(filepath)

    print('saving...')
    print(filepath)

    selectedObjects: List[bpy.types.Object] = []
    scn = context.view_layer
    for ob in scn.objects:
        if ob.select_get() and ob.type != 'ARMATURE':
            selectedObjects.append(ob)

    if len(selectedObjects) == 0:
        print('No objects selected for export.')
        operator.report({'WARNING'}, 'No objects selected for export')
        return {'CANCELLED'}

    try:
        export_info_log = []

        if context.active_object:
            bpy.ops.object.mode_set(mode='OBJECT')

        if apply_transform:
            bpy.ops.object.transform_apply(rotation=True, scale=True)

        log_file = os.path.join(os.path.dirname(os.path.realpath( __file__ )),
                                'log',
                                'kenshi_io_OGRE.log')
        serializer = KenshiObjectSerializer(logfile=log_file)
        armature = selectedObjects[0].find_armature()

        folder, filename = os.path.split(filepath)
        mesh_data = serializer.create_mesh(filename)

        skel_filename = '{}.skeleton'.format(os.path.splitext(filename)[0])
        skeleton_data = None
        if export_skeleton and armature:
            skeleton_data = serializer.create_skeleton(skel_filename)

        set_bones(export_info_log=export_info_log,
                  mesh_data=mesh_data,
                  skeleton_data=skeleton_data,
                  armature=armature,
                  export_all_bones=export_all_bones)

        set_mesh(context=context,
                 export_info_log=export_info_log,
                 mesh_data=mesh_data,
                 selected_objects=selectedObjects,
                 applyModifiers=apply_modifiers,
                 export_color=export_colour,
                 tangent_format=tangent_format,
                 export_poses=export_poses,
                 optimize=mesh_optimize)

        if skeleton_data:
            if export_animation:
                set_animations(context=context,
                               export_info_log=export_info_log,
                               skeleton_data=skeleton_data,
                               armature=armature,
                               is_visual_keying=is_visual_keying,
                               use_scale_keyframe=use_scale_keyframe)
            mesh_data.set_linked_skeleton_name(skel_filename)

        serializer.save_mesh(mesh_data, filepath, mesh_version)

        if skeleton_data:
            serializer.save_skeleton(skeleton_data, os.path.join(folder, skel_filename), skeleton_version)

        print('\n'.join(export_info_log))
        print('done.')
        operator.report({'INFO'}, 'Export successful')

    except:
        work_scene = context.blend_data.scenes.get('bake_work')
        if work_scene:
            context.blend_data.scenes.remove(work_scene)
        err_mes = traceback.format_exc()
        print(err_mes)
        operator.report({'ERROR'}, 'Export error!\n{}'.format(err_mes))

    return {'FINISHED'}


@func_timer
def save_skeleton(
        operator: bpy.types.Operator,
        context: bpy.types.Context,
        filepath: str,
        apply_transform: bool = True,
        export_animation: bool = False,
        export_all_bones: bool = False,
        export_version: str = 'V_1_10',
        is_visual_keying: bool = False,
        use_scale_keyframe: bool = False):
    if export_version == 'V_1_4':
        skeleton_version = SkeletonVersion.V_1_0
    else:
        skeleton_version = SkeletonVersion.V_Latest

    if not filepath.lower().endswith('.skeleton'):
        filepath = "{}.skeleton".format(filepath)

    print('saving...')
    print(filepath)

    selectedObjects: List[bpy.types.Object] = []
    scn = context.view_layer
    for ob in scn.objects:
        if ob.select_get() and ob.type == 'ARMATURE':
            selectedObjects.append(ob)

    if len(selectedObjects) == 0:
        print('No objects selected for export.')
        operator.report({'WARNING'}, 'No objects selected for export')
        return {'CANCELLED'}

    try:
        export_info_log = []

        if context.active_object:
            bpy.ops.object.mode_set(mode='OBJECT')

        if apply_transform:
            bpy.ops.object.transform_apply(rotation=True, scale=True)

        log_file = os.path.join(os.path.dirname(os.path.realpath( __file__ )),
                                'log',
                                'kenshi_io_OGRE.log')
        serializer = KenshiObjectSerializer(logfile=log_file)

        folder, skeleton_filename = os.path.split(filepath)
        skeleton_data = serializer.create_skeleton(skeleton_filename)

        armature = selectedObjects[0]
        set_bones(export_info_log=export_info_log,
                  mesh_data=None,
                  skeleton_data=skeleton_data,
                  armature=armature,
                  export_all_bones=export_all_bones)

        if armature:
            if export_animation:
                set_animations(context=context,
                               export_info_log=export_info_log,
                               skeleton_data=skeleton_data,
                               armature=armature,
                               is_visual_keying=is_visual_keying,
                               use_scale_keyframe=use_scale_keyframe)
            serializer.save_skeleton(skeleton_data, filepath, skeleton_version)

        print('\n'.join(export_info_log))
        print('done.')
        operator.report({'INFO'}, 'Export successful')

    except:
        work_scene = context.blend_data.scenes.get('bake_work')
        if work_scene:
            context.blend_data.scenes.remove(work_scene)
        err_mes = traceback.format_exc()
        print(err_mes)
        operator.report({'ERROR'}, 'Export error!\n{}'.format(err_mes))

    return {'FINISHED'}
