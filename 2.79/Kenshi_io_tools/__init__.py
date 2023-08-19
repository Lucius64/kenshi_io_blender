
bl_info = {
    "name": "Kenshi IO Tools (mesh, skeleton, collision)",
    "author": "Lucius",
    "blender": (2, 79, 0),
    "version": (1, 0, 0),
    "location": "File > Import-Export",
    "description": ("Import-Export Kenshi Model and collision files."),
    "warning": "",
    "wiki_url": "https://github.com/Lucius64/kenshi_io_tools",
    "tracker_url": "https://github.com/Lucius64/kenshi_io_tools",
    "support": 'COMMUNITY',
    "category": "Import-Export"}


if "bpy" in locals():
    import importlib
    if "ogre_importer" in locals():
        importlib.reload(ogre_importer)
    if "ogre_exporter" in locals():
        importlib.reload(ogre_exporter)
    if "physx_exporter" in locals():
        importlib.reload(physx_exporter)
    if "physx_importer" in locals():
        importlib.reload(physx_importer)
    if "util" in locals():
        importlib.reload(util)

import os

import bpy
from bpy.types import Operator, INFO_MT_file_import, INFO_MT_file_export, Scene
from bpy.props import BoolProperty, StringProperty, EnumProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.utils import register_class, unregister_class, previews

from . import ogre_importer
from . import ogre_exporter
from . import physx_importer
from . import physx_exporter
from .util import load_translate, code_page_list


class KENSHI_OT_ImportOgreObject(Operator, ImportHelper):
    '''Load an Ogre MESH File'''
    bl_idname = 'import.kenshi_ogre_objects'
    bl_label = 'Import MESH'
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = '.mesh'

    import_normals = BoolProperty(
        name='Import Normals',
        description='Import vertex normals (split normals)',
        default=True,
        )
    import_animations = BoolProperty(
        name='Import animation',
        description='Import skeletal animations as actions',
        default=True,
        )
    round_frames = BoolProperty(
        name='Adjust frame rate',
        description='Adjust scene frame rate to match imported animation',
        default=True,
        )
    import_shapekeys = BoolProperty(
        name='Import shape keys',
        description='Import shape keys (morphs)',
        default=True,
        )
    create_materials = BoolProperty(
        name='Create materials',
        description='Create materials (name only)',
        default=True,
        )
    use_selected_skeleton = BoolProperty(
        name='Use selected armature',
        description='''Link with selected armature when importing mesh.
skeleton is not imported.
Use this when importing gear meshes that don't have their own skeleton.
Make sure the correct armature is selected.
Weightmaps can get mixed up if not selected''',
        default=False,
        )
    select_encoding = EnumProperty(
        name='Encoding',
        description='If characters are not displayed correctly, try changing the character code',
        items=code_page_list(),
        default='utf-8',
        )
    use_filename = BoolProperty(
        name='Determine mesh name from file name',
        description="mesh name will be 'filename_number'",
        default=True,
        )
    filter_glob = StringProperty(
        default='*.mesh;*.MESH',
        options={'HIDDEN'},
        )

    def execute(self, context):
        keywords = self.as_keywords(ignore=('filter_glob',))
        bpy.context.window.cursor_set('WAIT')
        result = ogre_importer.load(self, context, **keywords)
        bpy.context.window.cursor_set('DEFAULT')
        return result

    def draw(self, context):
        layout = self.layout

        general = layout.box()
        general.label(text='Encoding')
        general.prop(self, 'select_encoding', text='')

        mesh = layout.box()
        mesh.prop(self, 'import_normals')
        mesh.prop(self, 'import_shapekeys')
        mesh.prop(self, 'create_materials')
        mesh.prop(self, 'use_filename')

        sleketon = layout.box()
        link = sleketon.column()
        link.enabled = True if context.active_object and context.active_object.type == 'ARMATURE' else False
        link.prop(self, 'use_selected_skeleton')
        sleketon.prop(self, 'import_animations')
        rate = sleketon.column()
        rate.enabled = self.import_animations
        rate.prop(self, 'round_frames')


class KENSHI_OT_ExportOgreObject(Operator, ExportHelper):
    '''Export a Kenshi MESH File'''
    bl_idname = 'export.kenshi_ogre_objects'
    bl_label = 'Export MESH'
    bl_options = {'PRESET'}
    filename_ext = '.mesh'

    export_version = EnumProperty(
        name='Mesh version',
        description='',
        items=[('V_1_10', 'version 1.10', 'The latest version that supports Kenshi'),
               ('V_1_8', 'version 1.8', 'Particle Universe Editor compatible version'),
               ('V_1_4', 'version 1.4', 'Scythe Physics Editor compatible version'),
               ],
        default='V_1_10',
        )
    tangent_format = EnumProperty(
        name='Tangent format',
        description='',
        items=[('TANGENT_3', 'tangent & binormal', 'Export tangent and binormal.'),
               ('TANGENT_4', 'tangent & bitangent sign', 'Export tangent and bitangent\'s signs.\nCompute the binormals at runtime.'),
               ('TANGENT_0', 'no tangent', 'Select if there is no UV map.'),
               ],
        default='TANGENT_3',
        )
    export_colour = BoolProperty(
        name='Export vertex colour',
        description="Export vertex colour data.\nName a colour layer 'Alpha' to use as the alpha component",
        default=False,
        )
    apply_transform = BoolProperty(
        name='Apply Transform',
        description="Applies object's transformation to its data",
        default=False,
        )
    apply_modifiers = BoolProperty(
        name='Apply Modifiers',
        description='Applies modifiers to the mesh',
        default=False,
        )
    export_poses = BoolProperty(
        name='Export shape keys',
        description='Export shape keys as poses',
        default=False,
        )
    mesh_optimize = BoolProperty(
        name='Optimize mesh',
        description='Remove duplicate vertices.\nThe conditions for duplication are that they have the same position, normal, tangent, bitangent, texture coordinates, and color',
        default=True,
        )
    export_skeleton = BoolProperty(
        name='Export skeleton',
        description='Exports new skeleton and links the mesh to this new skeleton.\nLeave off to link with existing skeleton if applicable.',
        default=False,
        )
    export_animation = BoolProperty(
        name="Export Animation",
        description='Export all actions attached to the selected skeleton as animations',
        default=False,
        )
    export_all_bones = BoolProperty(
        name="Include bones with undefined IDs",
        description="Export all bones.\nVertex weights and skeletal animation are also covered.",
        default=False,
        )
    is_visual_keying = BoolProperty(
        name='Visual Keying',
        description='''Set keyframes based on visuals.
More frames will slow down the export,
so it's a good idea to pre-bake the animation and uncheck this option''',
        default=False,
        )
    use_scale_keyframe = BoolProperty(
        name='Apply scale',
        description='Set scale keyframes in the animation',
        default=False,
        )
    filter_glob = StringProperty(
        default='*.mesh;*.MESH',
        options={'HIDDEN'},
        )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        keywords = self.as_keywords(ignore=('check_existing', 'filter_glob'))
        bpy.context.window.cursor_set('WAIT')
        result = ogre_exporter.save(self, context, **keywords)
        bpy.context.window.cursor_set('DEFAULT')
        return result

    def draw(self, context):
        layout = self.layout

        general = layout.box()
        general.label(text='Mesh version')
        general.prop(self, 'export_version', text='')
        general.prop(self, 'mesh_optimize')

        mesh = layout.box()
        mesh.label(text='Tangent format')
        mesh.prop(self, 'tangent_format', text='')
        mesh.prop(self, 'export_colour')
        mesh.prop(self, 'export_poses')
        mesh.prop(self, 'apply_transform')
        mesh.prop(self, 'apply_modifiers')

        skeleton = layout.box()
        skeleton.prop(self, 'export_skeleton')
        skeleton.prop(self, 'export_animation')
        keying = skeleton.column()
        keying.prop(self, 'is_visual_keying')
        keying.prop(self, 'use_scale_keyframe')
        keying.enabled = self.export_animation
        skeleton.prop(self, 'export_all_bones')


class KENSHI_OT_ImportOgreSkeletonObject(Operator, ImportHelper):
    '''Load an Ogre MESH File'''
    bl_idname = 'import.kenshi_ogre_skeleton_objects'
    bl_label = 'Import SKELETON'
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = '.skeleton'

    import_animations = BoolProperty(
        name='Import animation',
        description='Import skeletal animations as actions',
        default=True,
        )
    round_frames = BoolProperty(
        name='Adjust frame rate',
        description='Adjust scene frame rate to match imported animation',
        default=True,
        )
    use_selected_skeleton = BoolProperty(
        name='Use selected armature',
        description='Link animation to selected armature object',
        default=False,
        )
    filter_glob = StringProperty(
        default='*.skeleton;*.SKELETON',
        options={'HIDDEN'},
        )

    def execute(self, context):
        keywords = self.as_keywords(ignore=('filter_glob',))
        bpy.context.window.cursor_set('WAIT')
        result = ogre_importer.load_skeleton(self, context, **keywords)
        bpy.context.window.cursor_set('DEFAULT')
        return result

    def draw(self, context):
        layout = self.layout

        sleketon = layout.box()
        link = sleketon.column()
        link.enabled = True if context.active_object and context.active_object.type == 'ARMATURE' else False
        link.prop(self, 'use_selected_skeleton')
        sleketon.prop(self, 'import_animations')
        rate = sleketon.column()
        rate.enabled = self.import_animations
        rate.prop(self, 'round_frames')


class KENSHI_OT_ExportOgreSkeletonObject(Operator, ExportHelper):
    '''Export a Kenshi MESH File'''
    bl_idname = 'export.kenshi_ogre_skeleton_objects'
    bl_label = 'Export SKELETON'
    bl_options = {'PRESET'}
    filename_ext = '.skeleton'

    export_version = EnumProperty(
        name='Skeleton version',
        description='',
        items=[('V_1_10', 'version 1.10', 'The latest version that supports Kenshi'),
               ('V_1_4', 'version 1.4', 'Scythe Physics Editor compatible version'),
               ],
        default='V_1_10',
        )
    apply_transform = BoolProperty(
        name='Apply Transform',
        description="Applies object's transformation to its data",
        default=False,
        )
    export_animation = BoolProperty(
        name="Export Animation",
        description='Export all actions attached to the selected skeleton as animations',
        default=False,
        )
    export_all_bones = BoolProperty(
        name="Include bones with undefined IDs",
        description="Export all bones.\nVertex weights and skeletal animation are also covered.",
        default=False,
        )
    is_visual_keying = BoolProperty(
        name='Visual Keying',
        description='''Set keyframes based on visuals.
More frames will slow down the export,
so it's a good idea to pre-bake the animation and uncheck this option''',
        default=False,
        )
    use_scale_keyframe = BoolProperty(
        name='Apply scale',
        description='Set scale keyframes in the animation',
        default=False,
        )
    filter_glob = StringProperty(
        default='*.skeleton;*.SKELETON',
        options={'HIDDEN'},
        )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        keywords = self.as_keywords(ignore=('check_existing', 'filter_glob'))
        bpy.context.window.cursor_set('WAIT')
        result = ogre_exporter.save_skeleton(self, context, **keywords)
        bpy.context.window.cursor_set('DEFAULT')
        return result

    def draw(self, context):
        layout = self.layout

        general = layout.box()
        general.label(text='Skeleton version')
        general.prop(self, 'export_version', text='')

        skeleton = layout.box()
        skeleton.prop(self, 'apply_transform')
        skeleton.prop(self, 'export_animation')
        keying = skeleton.column()
        keying.prop(self, 'is_visual_keying')
        keying.prop(self, 'use_scale_keyframe')
        keying.enabled = self.export_animation
        skeleton.prop(self, 'export_all_bones')


class KENSHI_OT_ImportPhysXObject(Operator, ImportHelper):
    '''Import a Kenshi PhysX Collision File'''
    bl_idname = 'import.kenshi_physx_objects'
    bl_label = 'Import Collision'
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = '.xml'
    select_encoding = EnumProperty(
        name='Encoding',
        description='If characters are not displayed correctly, try changing the character code',
        items=code_page_list(),
        default='utf-8',
        )
    filter_glob = StringProperty(
        default='*.xml;*.XML',
        options={'HIDDEN'},
        )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        keywords = self.as_keywords(ignore=('check_existing', 'filter_glob'))
        bpy.context.window.cursor_set('WAIT')
        result = physx_importer.load(self, context, **keywords)
        bpy.context.window.cursor_set('DEFAULT')
        return result

    def draw(self, context):
        layout = self.layout
        layout.label(text='Encoding')
        layout.prop(self, 'select_encoding', text='')

        row = layout.row()
        row.template_icon_view(context.scene, "physx_logo")


class KENSHI_OT_ExportPhysXObject(Operator, ExportHelper):
    '''Export a Kenshi MESH File'''
    bl_idname = 'export.kenshi_physx_objects'
    bl_label = 'Export Collision'
    bl_options = {'PRESET'}
    filename_ext = '.xml'
    objects = EnumProperty(
        name='Objects',
        description='Which objects to export',
        items=[('ALL', 'All Objects', 'Export all collision objects in the scene'),
               ('SELECTED', 'Selection', 'Export only selected objects'),
               ('CHILDREN', 'Selected Children', 'Export selected objects and all their child objects'),
               ],
        default='CHILDREN',
        )
    transform = EnumProperty(
        name='Transform',
        description='Root transformation',
        items=[('SCENE', 'Scene', 'Export objects relative to scene origin'),
               ('PARENT', 'Parent', 'Export objects relative to common parent'),
               ('ACTIVE', 'Active', 'Export objects relative to the active object'),
               ],
        default='PARENT',
        )
    filter_glob = StringProperty(
        default='*.xml;*.XML',
        options={'HIDDEN'},
        )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        keywords = self.as_keywords(ignore=('check_existing', 'filter_glob'))
        bpy.context.window.cursor_set('WAIT')
        result = physx_exporter.save(self, context, **keywords)
        bpy.context.window.cursor_set('DEFAULT')
        return result

    def draw(self, context):
        layout = self.layout
        layout.label(text='Objects')
        layout.prop(self, 'objects', text='')
        layout.label(text='Transform')
        layout.prop(self, 'transform', text='')

        row = layout.row()
        row.template_icon_view(context.scene, "physx_logo")


def menu_func_import(self, context):
    self.layout.operator(KENSHI_OT_ImportOgreObject.bl_idname,
                         text='Kenshi OGRE (.mesh)')


def menu_func_export(self, context):
    self.layout.operator(KENSHI_OT_ExportOgreObject.bl_idname,
                         text='Kenshi OGRE (.mesh)')


def menu_func_import_skeleton(self, context):
    self.layout.operator(KENSHI_OT_ImportOgreSkeletonObject.bl_idname,
                         text='Kenshi OGRE (.skeleton)')


def menu_func_export_skeleton(self, context):
    self.layout.operator(KENSHI_OT_ExportOgreSkeletonObject.bl_idname,
                         text='Kenshi OGRE (.skeleton)')


def menu_func_import_collision(self, context):
    self.layout.operator(KENSHI_OT_ImportPhysXObject.bl_idname,
                         text='Kenshi Collision (.xml)')


def menu_func_export_collision(self, context):
    self.layout.operator(KENSHI_OT_ExportPhysXObject.bl_idname,
                         text='Kenshi Collision (.xml)')


classes = (KENSHI_OT_ImportOgreObject,
           KENSHI_OT_ExportOgreObject,
           KENSHI_OT_ImportOgreSkeletonObject,
           KENSHI_OT_ExportOgreSkeletonObject,
           KENSHI_OT_ImportPhysXObject,
           KENSHI_OT_ExportPhysXObject)

preview_collections = {}


def register():
    pcoll = previews.new()
    ui_images_dir = os.path.join(os.path.dirname(__file__), 'ui_images')
    physx_image = pcoll.load('PhysX_by_NVIDIA_Logo', os.path.join(ui_images_dir, 'PhysX_by_NVIDIA_Logo.png'), 'IMAGE')
    preview_collections['physx'] = pcoll

    Scene.physx_logo = EnumProperty(
        items=[('PhysX_by_NVIDIA_Logo', 'PhysX_by_NVIDIA_Logo', '', physx_image.icon_id, 0)]
        )

    for cls in classes:
        register_class(cls)

    INFO_MT_file_import.append(menu_func_import)
    INFO_MT_file_export.append(menu_func_export)
    INFO_MT_file_import.append(menu_func_import_skeleton)
    INFO_MT_file_export.append(menu_func_export_skeleton)
    INFO_MT_file_import.append(menu_func_import_collision)
    INFO_MT_file_export.append(menu_func_export_collision)

    bpy.app.translations.register(__name__, load_translate())


def unregister():
    bpy.app.translations.unregister(__name__)
    del Scene.physx_logo
    for pcoll in preview_collections.values():
        previews.remove(pcoll)
    preview_collections.clear()

    for cls in reversed(classes):
        unregister_class(cls)

    INFO_MT_file_import.remove(menu_func_import)
    INFO_MT_file_export.remove(menu_func_export)
    INFO_MT_file_import.remove(menu_func_import_skeleton)
    INFO_MT_file_export.remove(menu_func_export_skeleton)
    INFO_MT_file_import.remove(menu_func_import_collision)
    INFO_MT_file_export.remove(menu_func_export_collision)


if __name__ == "__main__":
    register()
