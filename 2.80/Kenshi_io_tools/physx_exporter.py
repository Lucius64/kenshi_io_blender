
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
        xCollection: ET.Element,
        xActor: ET.Element,
        obj: bpy.types.Object,
        transform: Matrix,
        physx: KenshiPhysXSerializer):
    mat, scale = remove_scale_from_matrix(transform @ obj.matrix_world)
    save_transform(xActor, 'globalPose', mat)
    bounds = shape_bounds(obj)
    print('bounds: ', bounds, ' scale: ', scale)

    xShape_attr = '{0:f} {1:f} {2:f}'.format(bounds[0] * scale[0] * 0.5,
                                             bounds[1] * scale[1] * 0.5,
                                             bounds[2] * scale[2] * 0.5)
    xShape = ET.SubElement(xActor,
                           'NxBoxShapeDesc',
                           attrib={'dimensions':xShape_attr})


def save_capsule_collision(
        xCollection: ET.Element,
        xActor: ET.Element,
        obj: bpy.types.Object,
        transform: Matrix,
        physx: KenshiPhysXSerializer):
    fix = Matrix([
        (1, 0, 0, 0),
        (0, 0, 1, 0),
        (0, 1, 0, 0),
        (0, 0, 0, 1)
        ])
    mat, scale = remove_scale_from_matrix(transform @ obj.matrix_world @ fix)
    save_transform(xActor, 'globalPose', mat)

    bounds = shape_bounds(obj)
    radius = 0.5 * max( abs(bounds[0] * scale[0]), abs(bounds[1] * scale[1]))
    xShape = ET.SubElement(xActor,
                           'NxCapsuleShapeDesc',
                           attrib={
                               'radius':'%6f' % radius,
                               'height':'%6f' % (abs(bounds[2]*scale[2]) - 2*radius)
                               })


def save_sphere_collision(
        xCollection: ET.Element,
        xActor: ET.Element,
        obj: bpy.types.Object,
        transform: Matrix,
        physx: KenshiPhysXSerializer):
    mat, scale = remove_scale_from_matrix(transform @ obj.matrix_world)
    save_transform(xActor, 'globalPose', mat)

    bounds = shape_bounds(obj)
    xShape = ET.SubElement(xActor,
                           'NxSphereShapeDesc',
                           attrib={'radius':str(max(bounds) * max(scale))})


def save_convex_collision(
        xCollection: ET.Element,
        xActor: ET.Element,
        obj: bpy.types.Object,
        transform: Matrix,
        physx: KenshiPhysXSerializer):
    mat, scale = remove_scale_from_matrix(transform @ obj.matrix_world)
    scaleMatrix = Matrix([
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
                                                                 scaleMatrix,
                                                                 collision_shape='CONVEX_HULL')

    obj.to_mesh_clear()

    xMesh = ET.SubElement(xCollection,
                          'NxConvexMeshDesc',
                          attrib={'id':obj.name})
    xMesh.append(elem_cooked_data_size)
    xMesh.append(elem_cooked_data)

    save_transform(xActor, 'globalPose', mat)

    xShape = ET.SubElement(xActor, 'NxConvexShapeDesc', attrib={'meshData':obj.name})


def save_mesh_collision(
        xCollection: ET.Element,
        xActor: ET.Element,
        obj: bpy.types.Object,
        transform: Matrix,
        physx: KenshiPhysXSerializer):
    mesh = obj.data if not obj.rigid_body.mesh_source == 'FINAL' else obj.to_mesh(preserve_all_data_layers=True)

    elem_cooked_data_size, elem_cooked_data = export_cooked_data(physx,
                                                                 mesh,
                                                                 transform @ obj.matrix_world,
                                                                 collision_shape='MESH')

    if obj.rigid_body.mesh_source == 'FINAL':
        obj.to_mesh_clear()

    xMesh = ET.SubElement(xCollection,
                          'NxTriangleMeshDesc',
                          attrib={'id':obj.name})
    xMesh.append(elem_cooked_data_size)
    xMesh.append(elem_cooked_data)
    xShape = ET.SubElement(xActor, 'NxTriangleMeshShapeDesc', attrib={'meshData':obj.name})


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
    if not a or not b:
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
            for ob in context.scene.objects:
                if hasCollision(operator, ob, shapeFunctions.keys()):
                    bodies.append(ob)
        elif objects == 'SELECTED':
            bodies = []
            for ob in context.scene.objects:
                if ob.select_get() and hasCollision(operator, ob, shapeFunctions.keys()):
                    bodies.append(ob)
        elif objects == 'CHILDREN':
            bodies: Set[bpy.types.Object] = set()
            for ob in context.scene.objects:
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
            root = bpy.context.scene.objects.active.matrix_world.inverted()
        elif transform == 'PARENT':
            parent = None
            for o in bodies:
                if not parent:
                    parent = o.parent
                    break
                else:
                    parent = commonParent(parent, o)
            if parent:
                root = parent.matrix_world.inverted()

        xRoot = ET.Element('NXUSTREAM2')
        xCollection = ET.SubElement(xRoot,
                                    'NxuPhysicsCollection',
                                    attrib={
                                        'id':os.path.basename(filepath),
                                        'sdkVersion':'284',
                                        'nxuVersion':'103'
                                        })
        xScene = ET.SubElement(xCollection,
                               'NxSceneDesc',
                               attrib={
                                   'id':'collision',
                                   'hasMaxBounds':'false',
                                   'hasLimits':'false',
                                   'hasFilter':'false'
                                   })

        physx = KenshiPhysXSerializer()

        for body in bodies:
            xActor = ET.SubElement(xScene,
                                   'NxActorDesc',
                                   attrib={
                                       'id':'name',
                                       'name':body.name,
                                       'hasBody':'false'
                                       })
            saveShape = shapeFunctions[body.rigid_body.collision_shape]
            saveShape(xCollection, xActor, body, root, physx)

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
        operator.report({'INFO'}, 'Import successful')

    except:
        err_mes = traceback.format_exc()
        print(err_mes)
        operator.report({'ERROR'}, 'Export error!\n{}'.format(err_mes))

    print('done.')
    return {'FINISHED'}
