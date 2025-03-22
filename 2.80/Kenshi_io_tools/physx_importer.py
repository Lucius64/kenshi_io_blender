
import xml.etree.ElementTree as ET
import re
import traceback
from typing import List, Tuple, Dict

import bpy
from mathutils import Matrix

from .util import func_timer
from .kenshi_blender_tool import KenshiPhysXSerializer, CollisionMesh


def isfloat(s: str):
    try:
        float(s)
    except ValueError:
        return False
    else:
        return True


def open_file(filename: str, encoding: str = 'utf-8'):
    with open(filename, encoding=encoding, errors='replace') as f:
        xml_text = f.read()
    content = r'&(?!amp;)'
    regex = re.compile(content)
    xml_text = regex.sub('&amp;', xml_text)
    output = ET.fromstring(xml_text)
    return output


def cooked_data_deserialize(
        physx: KenshiPhysXSerializer,
        cooked_data: str,
        cooked_data_size: str,
        collision_shape: str = 'CONVEX_HULL'):
    cooked_data = ''.join(cooked_data.split())
    coliision = None
    if collision_shape == 'CONVEX_HULL':
        coliision = physx.import_convex_hull(cooked_data)
    elif collision_shape == 'MESH':
        coliision = physx.import_triangle_mesh(cooked_data)
    else:
        raise ValueError('shape do not match CONVEX_HULL or MESH')

    verts = coliision.points
    faces = [coliision.triangles[i:i + 3] for i in range(0, len(coliision.triangles), 3)]
    return verts, faces


def pose_to_matrix(xml_actor: ET.Element, node_name: str):
    xml_pose = xml_actor.find(node_name)

    text_value = '' if xml_pose is None else xml_pose.text

    poses = []
    for i in text_value.split(' '):
        if len(i) == 0:
            continue

        if isfloat(i):
            poses.append(float(i))

    if len(poses) != 12:
        return Matrix([
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0)
            ])

    mat = Matrix([
        (poses[0], poses[1], poses[2], poses[9]),
        (poses[3], poses[4], poses[5], poses[10]),
        (poses[6], poses[7], poses[8], poses[11]),
        (0.0, 0.0, 0.0, 1.0)
        ])

    return mat


def create_empty_object(
        name: str,
        pose_mat: Matrix):
    scene = bpy.context.scene.collection
    layer = bpy.context.view_layer

    ob = bpy.data.objects.new(name, None)
    scene.objects.link(ob)

    ob.matrix_world = pose_mat
    ob.empty_display_type = 'ARROWS'

    layer.update()

    return ob


def create_mesh(
        name: str,
        parent_object: bpy.types.Object,
        pose_mat: Matrix,
        verts: List[Tuple],
        faces: List[Tuple] = [],
        edges: List[Tuple] = [],
        collision_shape = 'BOX'):
    scene = bpy.context.scene.collection
    layer = bpy.context.view_layer

    mesh_data = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, mesh_data)

    scene.objects.link(ob)
    layer.objects.active = ob
    layer.update()

    mesh_data.from_pydata(verts, edges, faces)
    mesh_data.update(calc_edges=True)
    if hasattr(mesh_data, 'use_auto_smooth'):
        mesh_data.use_auto_smooth = True

    if parent_object is not None:
        ob.parent = parent_object

    prev_active = layer.objects.active
    layer.objects.active = ob
    ob.matrix_local = pose_mat

    bpy.ops.rigidbody.object_add()
    ob.rigid_body.collision_shape = collision_shape
    ob.select_set(True)

    layer.objects.active = prev_active
    return ob


def create_box_shape(
        xml_actor: ET.Element,
        xml_physics: ET.Element,
        parent_objects: Dict[Matrix, bpy.types.Object]
        ):
    print('Import NxBoxShapeDesc')

    xml_NxBoxShapeDesc = xml_actor.find('NxBoxShapeDesc')
    if xml_NxBoxShapeDesc is None:
        return

    actor_name = xml_actor.get('name')

    global_mat = pose_to_matrix(xml_actor, 'globalPose')
    local_mat = pose_to_matrix(xml_NxBoxShapeDesc, 'NxShapeDesc/localPose')

    parent_mat = global_mat.freeze()
    parent_object = parent_objects.get(parent_mat)

    if not global_mat == Matrix() and parent_object is None:
        parent_object = create_empty_object('{}_root_{}'.format(actor_name, len(parent_objects)),
                                            parent_mat)
        parent_objects[parent_mat] = parent_object

    xml_dimensions = xml_NxBoxShapeDesc.get('dimensions')
    dimensions = []
    for i in xml_dimensions.split(' '):
        if len(i) == 0:
            continue

        if isfloat(i):
            dimensions.append(float(i))

    if len(dimensions) != 3:
        return

    verts = [
        (-dimensions[0], -dimensions[1], -dimensions[2]),
        (dimensions[0], -dimensions[1], -dimensions[2]),
        (dimensions[0], dimensions[1], -dimensions[2]),
        (-dimensions[0], dimensions[1], -dimensions[2]),
        (-dimensions[0], -dimensions[1], dimensions[2]),
        (dimensions[0], -dimensions[1], dimensions[2]),
        (dimensions[0], dimensions[1], dimensions[2]),
        (-dimensions[0], dimensions[1], dimensions[2])
    ]

    faces = [
        (0, 1, 2, 3),
        (4, 5, 6, 7),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0)
        ]

    shape = create_mesh(name=actor_name,
                        parent_object=parent_object,
                        verts=verts,
                        faces=faces,
                        pose_mat=local_mat,
                        collision_shape='BOX')


def create_sphere_shape(
        xml_actor: ET.Element,
        xml_physics: ET.Element,
        parent_objects: Dict[Matrix, bpy.types.Object]):
    print('Import NxSphereShapeDesc')

    xml_NxSphereShapeDesc = xml_actor.find('NxSphereShapeDesc')
    if xml_NxSphereShapeDesc is None:
        return

    actor_name = xml_actor.get('name')

    global_mat = pose_to_matrix(xml_actor, 'globalPose')
    local_mat = pose_to_matrix(xml_NxSphereShapeDesc, 'NxShapeDesc/localPose')

    parent_mat = global_mat.freeze()
    parent_object = parent_objects.get(parent_mat)

    if not global_mat == Matrix() and parent_object is None:
        parent_object = create_empty_object('{}_root_{}'.format(actor_name, len(parent_objects)),
                                            parent_mat)
        parent_objects[parent_mat] = parent_object

    radius = xml_NxSphereShapeDesc.get('radius')
    half_radius = float(radius) * 0.5

    verts = [
        (-half_radius, -half_radius, -half_radius),
        (half_radius, -half_radius, -half_radius),
        (half_radius, half_radius, -half_radius),
        (-half_radius, half_radius, -half_radius),
        (-half_radius, -half_radius, half_radius),
        (half_radius, -half_radius, half_radius),
        (half_radius, half_radius, half_radius),
        (-half_radius, half_radius, half_radius)
    ]

    faces = [
        (0, 1, 2, 3),
        (4, 5, 6, 7),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0)
        ]

    shape = create_mesh(name=actor_name,
                        parent_object=parent_object,
                        verts=verts,
                        faces=faces,
                        pose_mat=local_mat,
                        collision_shape='SPHERE')

    shape.display_type = 'BOUNDS'


def create_capsule_shape(
        xml_actor: ET.Element,
        xml_physics: ET.Element,
        parent_objects: Dict[Matrix, bpy.types.Object]):
    print('Import NxCapsuleShapeDesc')

    xml_NxCapsuleShapeDesc = xml_actor.find('NxCapsuleShapeDesc')
    if xml_NxCapsuleShapeDesc is None:
        return

    fix = Matrix([
        (1, 0, 0, 0),
        (0, 0, 1, 0),
        (0, 1, 0, 0),
        (0, 0, 0, 1)
        ])

    actor_name = xml_actor.get('name')

    global_mat = pose_to_matrix(xml_actor, 'globalPose')
    local_mat = pose_to_matrix(xml_NxCapsuleShapeDesc, 'NxShapeDesc/localPose')

    parent_mat = global_mat.freeze()
    parent_object = parent_objects.get(parent_mat)

    if not global_mat == Matrix() and parent_object is None:
        parent_object = create_empty_object('{}_root_{}'.format(actor_name, len(parent_objects)),
                                            parent_mat)
        parent_objects[parent_mat] = parent_object

    radius = xml_NxCapsuleShapeDesc.get('radius')
    height = xml_NxCapsuleShapeDesc.get('height')
    half_radius = float(radius)
    half_height = float(height) * 0.5 + half_radius

    verts = [
        (-half_radius, -half_radius, -half_height),
        (half_radius, -half_radius, -half_height),
        (half_radius, half_radius, -half_height),
        (-half_radius, half_radius, -half_height),
        (-half_radius, -half_radius, half_height),
        (half_radius, -half_radius, half_height),
        (half_radius, half_radius, half_height),
        (-half_radius, half_radius, half_height)
    ]

    faces = [
        (0, 1, 2, 3),
        (4, 5, 6, 7),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0)
        ]

    shape = create_mesh(name=actor_name,
                        parent_object=parent_object,
                        verts=verts,
                        faces=faces,
                        pose_mat=local_mat @ fix,
                        collision_shape='CAPSULE')

    shape.display_type = 'BOUNDS'


def create_convex_shape(
        xml_actor: ET.Element,
        xml_physics: ET.Element,
        parent_objects: Dict[Matrix, bpy.types.Object],
        physx: KenshiPhysXSerializer):
    print('Import NxConvexShapeDesc')

    xml_NxConvexShapeDesc = xml_actor.find('NxConvexShapeDesc')
    if xml_NxConvexShapeDesc is None:
        return

    actor_name = xml_actor.get('name')

    global_mat = pose_to_matrix(xml_actor, 'globalPose')
    local_mat = pose_to_matrix(xml_NxConvexShapeDesc, 'NxShapeDesc/localPose')

    parent_mat = global_mat.freeze()
    parent_object = parent_objects.get(parent_mat)

    if not global_mat == Matrix() and parent_object is None:
        parent_object = create_empty_object('{}_root_{}'.format(actor_name, len(parent_objects)),
                                            parent_mat)
        parent_objects[parent_mat] = parent_object

    verts = []
    faces = []

    mesh_id = xml_NxConvexShapeDesc.get('meshData')

    xml_NxConvexMeshDesc = xml_physics.find("NxConvexMeshDesc[@id='{}']".format(mesh_id))
    if xml_NxConvexMeshDesc is not None:
        xml_points = xml_NxConvexMeshDesc.find('points')
        xml_triangles = xml_NxConvexMeshDesc.find('triangles')
        xml_cooked_data = xml_NxConvexMeshDesc.find('cookedData')
        xml_cooked_data_size = xml_NxConvexMeshDesc.find('cookedDataSize')

        if (xml_points is not None
                and xml_triangles is not None
                and xml_points.text is not None
                and xml_triangles.text is not None):
            points = xml_points.text.split(' ')
            triangles = xml_triangles.text.split(' ')

            verts = [[float(points[i]), float(points[i + 1]), float(points[i + 2])] for i in range(0, len(points), 3)]
            faces = [[int(triangles[i]), int(triangles[i + 1]), int(triangles[i + 2])] for i in range(0, len(triangles), 3)]

        if (len(verts) == 0
                and len(faces) == 0
                and xml_cooked_data is not None
                and xml_cooked_data_size is not None
                and xml_cooked_data.text is not None
                and xml_cooked_data_size.text is not None):
            verts, faces = cooked_data_deserialize(physx,
                                                   xml_cooked_data.text,
                                                   xml_cooked_data_size.text,
                                                   collision_shape='CONVEX_HULL')

        if len(verts) == 0 or len(faces) == 0:
            return

        shape = create_mesh(name=actor_name,
                            parent_object=parent_object,
                            verts=verts,
                            faces=faces,
                            pose_mat=local_mat,
                            collision_shape='CONVEX_HULL')


def create_triangle_mesh_shape(
        xml_actor: ET.Element,
        xml_physics: ET.Element,
        parent_objects: Dict[Matrix, bpy.types.Object],
        physx: KenshiPhysXSerializer):
    print('Import NxTriangleMeshShapeDesc')

    xml_NxTriangleMeshShapeDesc = xml_actor.find('NxTriangleMeshShapeDesc')
    if xml_NxTriangleMeshShapeDesc is None:
        return

    actor_name = xml_actor.get('name')

    global_mat = pose_to_matrix(xml_actor, 'globalPose')
    local_mat = pose_to_matrix(xml_NxTriangleMeshShapeDesc, 'NxShapeDesc/localPose')

    parent_mat = global_mat.freeze()
    parent_object = parent_objects.get(parent_mat)

    if not global_mat == Matrix() and parent_object is None:
        parent_object = create_empty_object('{}_root_{}'.format(actor_name, len(parent_objects)),
                                            parent_mat)
        parent_objects[parent_mat] = parent_object

    verts = []
    faces = []

    mesh_id = xml_NxTriangleMeshShapeDesc.get('meshData')

    xml_NxTriangleMeshDesc = xml_physics.find("NxTriangleMeshDesc[@id='{}']".format(mesh_id))
    if xml_NxTriangleMeshDesc is not None:
        xml_points = xml_NxTriangleMeshDesc.find('NxSimpleTriangleMesh/points')
        xml_triangles = xml_NxTriangleMeshDesc.find('NxSimpleTriangleMesh/triangles')
        xml_cooked_data = xml_NxTriangleMeshDesc.find('cookedData')
        xml_cooked_data_size = xml_NxTriangleMeshDesc.find('cookedDataSize')

        if (xml_points is not None
                and xml_triangles is not None
                and xml_points.text is not None
                and xml_triangles.text is not None):
            points = xml_points.text.split(' ')
            triangles = xml_triangles.text.split(' ')

            verts = [[float(points[i]), float(points[i + 1]), float(points[i + 2])] for i in range(0, len(points), 3)]
            faces = [[int(triangles[i]), int(triangles[i + 1]), int(triangles[i + 2])] for i in range(0, len(triangles), 3)]

        if (len(verts) == 0
                and len(faces) == 0
                and xml_cooked_data is not None
                and xml_cooked_data_size is not None
                and xml_cooked_data.text is not None
                and xml_cooked_data_size.text is not None):
            verts, faces = cooked_data_deserialize(physx,
                                                   xml_cooked_data.text,
                                                   xml_cooked_data_size.text,
                                                   collision_shape='MESH')

        if len(verts) == 0 or len(faces) == 0:
            return

        shape = create_mesh(name=actor_name,
                            parent_object=parent_object,
                            verts=verts,
                            faces=faces,
                            pose_mat=local_mat,
                            collision_shape='MESH')


@func_timer
def load(
        operator: bpy.types.Operator,
        context: bpy.types.Context,
        filepath: str,
        select_encoding='utf-8'):

    try:
        print('loading', filepath)

        if not filepath.lower().endswith('.xml'):
            return {'CANCELLED'}

        physx = KenshiPhysXSerializer()

        nxustream2 = open_file(filepath, encoding=select_encoding)

        if nxustream2 is None:
            return {'CANCELLED'}

        bpy.ops.object.select_all(action='DESELECT')

        parent_objects: Dict[Matrix, bpy.types.Object] = {}

        physics_collection = nxustream2.find('NxuPhysicsCollection')
        sence_desc = nxustream2.find('NxuPhysicsCollection/NxSceneDesc')

        if physics_collection is not None and sence_desc is not None:
            for actor_desc in sence_desc.findall('NxActorDesc'):
                if actor_desc.find('NxBoxShapeDesc') is not None:
                    create_box_shape(actor_desc, physics_collection, parent_objects)

                if actor_desc.find('NxSphereShapeDesc') is not None:
                    create_sphere_shape(actor_desc, physics_collection, parent_objects)

                if actor_desc.find('NxCapsuleShapeDesc') is not None:
                    create_capsule_shape(actor_desc, physics_collection, parent_objects)

                if actor_desc.find('NxConvexShapeDesc') is not None:
                    create_convex_shape(actor_desc, physics_collection, parent_objects, physx)

                if actor_desc.find('NxTriangleMeshShapeDesc') is not None:
                    create_triangle_mesh_shape(actor_desc, physics_collection, parent_objects, physx)
        operator.report({'INFO'}, 'Import successful')

    except:
        err_mes = traceback.format_exc()
        print(err_mes)
        operator.report({'ERROR'}, 'Import error!\n{}'.format(err_mes))

    print('done.')
    return {'FINISHED'}
