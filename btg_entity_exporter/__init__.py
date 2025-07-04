import bpy
from . import entity
from . import operators
from . import panels
from . import utilities
import importlib

if 'bpy' in locals():
    importlib.reload(entity)
    importlib.reload(operators)
    importlib.reload(panels)
    importlib.reload(utilities)

bl_info = {
    'name': 'Blender To Godot Pipeline',
    'author': 'Nathan Zimmer',
    'version': (1, 0, 0),
    'blender': (4, 2, 0),
    'category': 'Object',
}


# Setup Scene and object variables
def register():
    entity.register()
    operators.register()
    panels.register()

    # load/save functions
    if utilities.load_template not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(utilities.load_template)

    if utilities.export_on_save not in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.append(utilities.export_on_save)

    # File IO
    bpy.types.Scene.entity_template_path = bpy.props.StringProperty(
        name='Entity template path',
        description='The path of your Godot entity template JSON',
        subtype='FILE_PATH',
    )
    bpy.types.Scene.btg_write_path = bpy.props.StringProperty(
        name='Entity definition write-path',
        description=(
            'The path to write your entity definition import JSON. You have to write '
            'out this JSON in order to use the import script in Godot.'
        ),
        subtype='FILE_PATH',
    )
    bpy.types.Scene.export_on_save = bpy.props.BoolProperty(
        name='Export on save',
        description=('Write out entity definition JSON whenever the file is saved.'),
        default=False,
    )

    # Entity definition
    bpy.types.Object.class_name = bpy.props.EnumProperty(
        items=utilities.get_class_list,
        update=utilities.reset_class_definition,
        description='The Godot class of this object',
        default=0,
    )
    # Stores the class_name as a string rather than an index in the enum.
    # This is used when the enum is updated and we need to check if the class
    # order has changed.
    bpy.types.Object.class_name_backup = bpy.props.StringProperty()
    bpy.types.Object.class_definition = bpy.props.PointerProperty(
        type=entity.EntityDefinition,
        override={'LIBRARY_OVERRIDABLE'},
    )
    bpy.types.Scene.entity_template = bpy.props.PointerProperty(
        type=entity.EntityTemplate,
        override={'LIBRARY_OVERRIDABLE'},
    )

    # Property searching
    bpy.types.Scene.search_class_name = bpy.props.EnumProperty(
        name='Godot Entities',
        description='The Godot class to search for',
        items=utilities.get_class_list,
        update=utilities.set_search_property,
        default=0,
    )
    bpy.types.Scene.search_type = bpy.props.EnumProperty(
        items=[
            ('class', 'Class name', 'Select all objects of this class'),
            ('var_val', 'Variable value', 'Select all objects with this variable value'),
        ],
        description='Search type',
        default=0,
    )
    bpy.types.Scene.comparison_type = bpy.props.EnumProperty(
        items=[
            ('<', '<', 'less than'),
            ('<=', '<=', 'less than or equal to'),
            ('==', '==', 'equal to'),
            ('>', '>', 'greater than'),
            ('>=', '>=', 'greater than or equal to'),
        ],
        description='Type of evaluation to use',
        default='==',
    )
    bpy.types.Scene.search_var_name = bpy.props.EnumProperty(
        name='Godot Entity variables',
        description='Variable to search for',
        items=utilities.get_variable_search_list,
        update=utilities.set_search_property,
        default=0,
    )
    bpy.types.Scene.search_property = bpy.props.PointerProperty(type=entity.EntityProperty)


def unregister():
    entity.unregister()
    operators.unregister()
    panels.unregister()

    # load/save functions
    if utilities.load_template in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(utilities.load_template)

    if utilities.export_on_save in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(utilities.export_on_save)

    # File IO
    del bpy.types.Scene.entity_template_path
    del bpy.types.Scene.btg_write_path
    del bpy.types.Scene.export_on_save

    # Entity definition
    del bpy.types.Object.class_name
    del bpy.types.Object.class_name_backup
    del bpy.types.Object.class_definition
    del bpy.types.Scene.entity_template

    # Property searching
    del bpy.types.Scene.search_class_name
    del bpy.types.Scene.search_type
    del bpy.types.Scene.comparison_type
    del bpy.types.Scene.search_var_name
    del bpy.types.Scene.search_property


if __name__ == '__main__':
    register()
