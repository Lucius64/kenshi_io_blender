
import os
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom
import traceback
from typing import Set

import bpy
import bmesh
from mathutils import Matrix

from .util import func_timer
sys.path.append(os.path.dirname(__file__))
from Kenshi_blender_tool import KenshiPhysXSerializer


def shape_bounds(obj: bpy.types.Object):
    x = obj.bound_box[6][0] - obj.bound_box[0][0]
    y = obj.bound_box[6][1] - obj.bound_box[0][1]
    z = obj.bound_box[6][2] - obj.bound_box[0][2]
    return (x, y, z)


def remove_scale_from_matrix(m: Matrix):
    loc, rot, sca = m.decompose()
    m =  Matrix.Translation(loc) @ rot.to_matrix().to_4x4()
    return (m, sca)


def export_cooked_data(
        physx: KenshiPhysXSerializer,
        mesh: bpy.types.Mesh,
        transform: Matrix,
        collision_shape: str = 'CONVEX_HULL'):
    vertices = []
    for vx in mesh.vertices:
        v = transform @ vx.co
        vertices.append([v[0], v[1], v[2]])

    mesh.calc_loop_triangles()
    triangles = [v for tri in mesh.loop_triangles for v in tri.vertices]

    cooked_data = ''
    if collision_shape == 'CONVEX_HULL':
        cooked_data = physx.export_convex_hull(vertices)
    elif collision_shape == 'MESH':
        cooked_data = physx.export_triangle_mesh(vertices, triangles)
    else:
        raise ValueError('shape do not match CONVEX_HULL or MESH')

    elem_cooked_data_size = ET.Element('cookedDataSize')
    elem_cooked_data_size.text = str(int(len(cooked_data) / 2))
    elem_cooked_data = ET.Element('cookedData')
    elem_cooked_data.text = str(cooked_data)
    return elem_cooked_data_size, elem_cooked_data


def save_box_collision(
        physics_collection: ET.Element,
        actor_desc: ET.Element,
        obj: bpy.types.Object,
        parent: Matrix,
        physx: KenshiPhysXSerializer):
    parent_mat, _ = remove_scale_from_matrix(parent)
    local_mat, scale = remove_scale_from_matrix(parent_mat.inverted() @ obj.matrix_world)
    unit_scl_mat = Matrix.Scale(1, 4) if scale.x >= 0 else Matrix.Scale(-1, 4)
    save_transform(actor_desc, 'globalPose', parent_mat)
    bounds = shape_bounds(obj)
    print('bounds: ', bounds, ' scale: ', scale)

    shape_attr = '{0:f} {1:f} {2:f}'.format(abs(bounds[0] * scale[0] * 0.5),
                                            abs(bounds[1] * scale[1] * 0.5),
                                            abs(bounds[2] * scale[2] * 0.5))
    box_shape_desc = ET.SubElement(actor_desc,
                                   'NxBoxShapeDesc',
                                   attrib={'dimensions':shape_attr})

    shape_desc = ET.SubElement(box_shape_desc,
                               'NxShapeDesc',
                               attrib={'name':obj.name})

    save_transform(shape_desc, 'localPose', local_mat @ unit_scl_mat)


def save_capsule_collision(
        physics_collection: ET.Element,
        actor_desc: ET.Element,
        obj: bpy.types.Object,
        parent: Matrix,
        physx: KenshiPhysXSerializer):
    fix = Matrix([
        (1, 0, 0, 0),
        (0, 0, 1, 0),
        (0, 1, 0, 0),
        (0, 0, 0, 1)
        ])
    parent_mat, _ = remove_scale_from_matrix(parent)
    local_mat, scale = remove_scale_from_matrix(parent_mat.inverted() @ obj.matrix_world @ fix)
    unit_scl_mat = Matrix.Scale(1, 4) if scale.x >= 0 else Matrix.Scale(-1, 4)
    save_transform(actor_desc, 'globalPose', parent_mat)

    bounds = shape_bounds(obj)
    radius = 0.5 * max( abs(bounds[0] * scale[0]), abs(bounds[1] * scale[1]))

    capsule_shape_desc = ET.SubElement(actor_desc,
                                       'NxCapsuleShapeDesc',
                                       attrib={
                                           'radius':'%6f' % radius,
                                           'height':'%6f' % (abs(bounds[2] * scale[2]) - 2 * radius)
                                       })

    shape_desc = ET.SubElement(capsule_shape_desc,
                               'NxShapeDesc',
                               attrib={'name':obj.name})

    save_transform(shape_desc, 'localPose', local_mat @ unit_scl_mat)


def save_sphere_collision(
        physics_collection: ET.Element,
        actor_desc: ET.Element,
        obj: bpy.types.Object,
        parent: Matrix,
        physx: KenshiPhysXSerializer):
    parent_mat, _ = remove_scale_from_matrix(parent)
    local_mat, scale = remove_scale_from_matrix(parent_mat.inverted() @ obj.matrix_world)
    unit_scl_mat = Matrix.Scale(1, 4) if scale.x >= 0 else Matrix.Scale(-1, 4)
    save_transform(actor_desc, 'globalPose', parent_mat)

    bounds = shape_bounds(obj)

    sphere_shape_desc = ET.SubElement(actor_desc,
                                      'NxSphereShapeDesc',
                                      attrib={'radius':str(abs(max(bounds) * max(scale)))})

    shape_desc = ET.SubElement(sphere_shape_desc,
                               'NxShapeDesc',
                               attrib={'name':obj.name})

    save_transform(shape_desc, 'localPose', local_mat @ unit_scl_mat)


def save_convex_collision(
        physics_collection: ET.Element,
        actor_desc: ET.Element,
        obj: bpy.types.Object,
        parent: Matrix,
        physx: KenshiPhysXSerializer):
    parent_mat, _ = remove_scale_from_matrix(parent)
    local_mat, scale = remove_scale_from_matrix(parent_mat.inverted() @ obj.matrix_world)
    scale_matrix = Matrix([
        (scale[0], 0, 0, 0),
        (0, scale[1], 0, 0),
        (0, 0, scale[2], 0),
        (0, 0, 0, 1)
        ])

    apply_modifiers = obj.rigid_body.mesh_source == 'FINAL'
    mesh = obj.to_mesh(preserve_all_data_layers=apply_modifiers)

    bm = bmesh.new()
    bm.from_mesh(mesh)
    r = bmesh.ops.convex_hull(bm, input=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    del bm

    elem_cooked_data_size, elem_cooked_data = export_cooked_data(physx,
                                                                 mesh,
                                                                 scale_matrix,
                                                                 collision_shape='CONVEX_HULL')

    obj.to_mesh_clear()

    mesh_desc = ET.SubElement(physics_collection,
                              'NxConvexMeshDesc',
                              attrib={'id':obj.name})
    mesh_desc.append(elem_cooked_data_size)
    mesh_desc.append(elem_cooked_data)

    save_transform(actor_desc, 'globalPose', parent_mat)

    convex_shape_desc = ET.SubElement(actor_desc, 'NxConvexShapeDesc', attrib={'meshData':obj.name})

    shape_desc = ET.SubElement(convex_shape_desc,
                               'NxShapeDesc',
                               attrib={'name':obj.name})

    save_transform(shape_desc, 'localPose', local_mat)


def save_mesh_collision(
        physics_collection: ET.Element,
        actor_desc: ET.Element,
        obj: bpy.types.Object,
        parent: Matrix,
        physx: KenshiPhysXSerializer):
    parent_mat, _ = remove_scale_from_matrix(parent)
    local_mat, scale = remove_scale_from_matrix(parent_mat.inverted() @ obj.matrix_world)
    scale_matrix = Matrix([
        (scale[0], 0, 0, 0),
        (0, scale[1], 0, 0),
        (0, 0, scale[2], 0),
        (0, 0, 0, 1)
        ])

    mesh = obj.data if not obj.rigid_body.mesh_source == 'FINAL' else obj.to_mesh(preserve_all_data_layers=True)

    elem_cooked_data_size, elem_cooked_data = export_cooked_data(physx,
                                                                 mesh,
                                                                 scale_matrix,
                                                                 collision_shape='MESH')

    if obj.rigid_body.mesh_source == 'FINAL':
        obj.to_mesh_clear()

    mesh_desc = ET.SubElement(physics_collection,
                              'NxTriangleMeshDesc',
                              attrib={'id':obj.name})
    mesh_desc.append(elem_cooked_data_size)
    mesh_desc.append(elem_cooked_data)

    save_transform(actor_desc, 'globalPose', parent_mat)

    triangle_mesh_shape_desc = ET.SubElement(actor_desc, 'NxTriangleMeshShapeDesc', attrib={'meshData':obj.name})

    shape_desc = ET.SubElement(triangle_mesh_shape_desc,
                               'NxShapeDesc',
                               attrib={'name':obj.name})

    save_transform(shape_desc, 'localPose', local_mat)


def save_transform(xObject: ET.Element, name: str, m):
    mat = '{0:f} {1:f} {2:f}  {3:f} {4:f} {5:f}  {6:f} {7:f} {8:f}  {9:f} {10:f} {11:f}'.format(m[0][0],
                                                                                                m[0][1],
                                                                                                m[0][2],
                                                                                                m[1][0],
                                                                                                m[1][1],
                                                                                                m[1][2],
                                                                                                m[2][0],
                                                                                                m[2][1],
                                                                                                m[2][2],
                                                                                                m[0][3],
                                                                                                m[1][3],
                                                                                                m[2][3])
    xTransform = ET.SubElement(xObject, name)
    xTransform.text = mat


def hasCollision(operator: bpy.types.Operator, object: bpy.types.Object, types):
    if not object.rigid_body:
        return False
    if object.rigid_body.collision_shape in types:
        return True
    operator.report({'WARNING'}, 'Unsupported collision shape : {}'.format(object.rigid_body.collision_shape))
    return False


def addChildrenToSet(operator: bpy.types.Operator,
                     object: bpy.types.Object,
                     set: Set[bpy.types.Object],
                     types):
    for child in object.children:
        if hasCollision(operator, child, types):
            set.add(child)
        addChildrenToSet(operator, child, set, types)


def commonParent(a: bpy.types.Object, b: bpy.types.Object):
    if a is None or b is None:
        return None
    # depth in tree
    da = 0
    db = 0
    p = a
    while p:
        da += 1
        p = p.parent
    p = b
    while p:
        db += 1
        p = p.parent

    while da > db:
        da -= 1
        a = a.parent
    while db > da:
        db -= 1
        b = b.parent

    while a != b:
        a = a.parent
        b = b.parent

    return a


@func_timer
def save(
        operator: bpy.types.Operator,
        context: bpy.types.Context,
        filepath: str,
        objects: str = 'ALL',
        transform: str = 'SCENE'):
    try:
        script_dir = os.path.dirname(os.path.realpath( __file__ ))
        os.environ['PATH'] = '{};{}'.format(script_dir, os.environ['PATH'])

        if not filepath.lower().endswith('.xml'):
            filepath = '{}.xml'.format(filepath)
        print('Saving', filepath)

        for ob in bpy.data.objects:
            bpy.ops.object.mode_set(mode='OBJECT')

        shapeFunctions = {'BOX': save_box_collision,
                          'SPHERE': save_sphere_collision, 
                          'CAPSULE': save_capsule_collision,
                          'CONVEX_HULL': save_convex_collision,
                          'MESH': save_mesh_collision}

        bodies = None
        if objects == 'ALL':
            bodies = []
            for ob in context.view_layer.objects:
                if hasCollision(operator, ob, shapeFunctions.keys()):
                    bodies.append(ob)
        elif objects == 'SELECTED':
            bodies = []
            for ob in context.view_layer.objects:
                if ob.select_get() and hasCollision(operator, ob, shapeFunctions.keys()):
                    bodies.append(ob)
        elif objects == 'CHILDREN':
            bodies: Set[bpy.types.Object] = set()
            for ob in context.view_layer.objects:
                if ob.select_get():
                    if hasCollision(operator, ob, shapeFunctions.keys()):
                        bodies.add(ob)
                    addChildrenToSet(operator, ob, bodies, shapeFunctions.keys())

        if len(bodies) == 0:
            print('No collision to export.')
            operator.report({'WARNING'}, 'No collision selected for export')
            return {'CANCELLED'}

        root = Matrix()
        if transform == 'ACTIVE':
            active_obj: bpy.types.Object = context.view_layer.objects.active
            root = active_obj.matrix_world
            print('root object:', active_obj.name)
        elif transform == 'PARENT':
            parent = None
            for o in bodies:
                if not parent:
                    parent = o.parent
                    break
                else:
                    parent = commonParent(parent, o)
            if parent is not None:
                print('root object:', parent.name)
                root = parent.matrix_world

        xRoot = ET.Element('NXUSTREAM2')
        physics_collection = ET.SubElement(xRoot,
                                           'NxuPhysicsCollection',
                                           attrib={
                                               'id':os.path.basename(filepath),
                                               'sdkVersion':'284',
                                               'nxuVersion':'103'
                                           })
        scene_desc = ET.SubElement(physics_collection,
                                   'NxSceneDesc',
                                   attrib={
                                       'id':'collision',
                                       'hasMaxBounds':'false',
                                       'hasLimits':'false',
                                       'hasFilter':'false'
                                   })

        physx = KenshiPhysXSerializer()

        for body in bodies:
            actor_desc = ET.SubElement(scene_desc,
                                       'NxActorDesc',
                                       attrib={
                                           'id':'name',
                                           'name':body.name,
                                           'hasBody':'false'
                                       })
            saveShape = shapeFunctions[body.rigid_body.collision_shape]
            parent_matrix = root
            if transform == 'OWN_PARENT' and body.parent is not None:
                parent_matrix = body.parent.matrix_world
            saveShape(physics_collection, actor_desc, body, parent_matrix, physx)

        blender_version = bpy.app.version[0] * 100 + bpy.app.version[1]
        if blender_version >= 290:
            tree = ET.ElementTree(xRoot)
            ET.indent(tree, space='    ')
            tree.write(filepath, encoding='UTF-8', xml_declaration=True)
        else:
            document = minidom.parseString(ET.tostring(xRoot, 'utf-8'))
            data = document.toprettyxml(indent='    ')
            with open(filepath, 'wb') as f:
                f.write(bytes(data,'utf-8'))
                f.close()
        operator.report({'INFO'}, 'Export successful')

    except:
        err_mes = traceback.format_exc()
        print(err_mes)
        operator.report({'ERROR'}, 'Export error!\n{}'.format(err_mes))

    print('done.')
    return {'FINISHED'}
