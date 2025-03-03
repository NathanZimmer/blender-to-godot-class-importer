bl_info = {
    'name': 'Blender To Godot Pipeline',
    'author': 'Nathan Zimmer',
    'version': (0, 1, 0),
    'blender': (4, 2, 0),
    'category': 'Object',
}

import bpy
from . import entity
from . import operators
from . import panels

import importlib
if 'bpy' in locals():
    importlib.reload(entity)
    importlib.reload(operators)
    importlib.reload(panels)

# Utility functions
def reset_class_definition(self, context) -> None:
    """
    Reset `self.class_definition` and populate with new variables
    from new `context.scene.entity_template[self.class_name]`
    """
    self.class_definition.clear()
    self.class_name_backup = self.class_name

    if self.class_name == 'None':
        return

    class_def = context.scene.entity_template[self.class_name]

    for var_name, var_def in class_def['variables'].items():
        # var_type, var_default, var_desc, var_items = var_def
        var_type = var_def['type']
        var_default = var_def['default']
        var_desc = var_def['description']
        var_desc = var_def.get('description', '')
        var_items = var_def.get('options', [])

        self.class_definition.add(
            name=var_name,
            type=var_type,
            value=var_default,
            description=var_desc,
            items=var_items
        )

def set_search_property(self, context) -> None:
    """
    Set the Scene search property based on `scene.search_class_name` and
    `scene.search_var_name`
    """
    class_name = self.search_class_name
    var_name = self.search_var_name
    var_def = self.entity_template[class_name]['variables'][var_name]
    var_type = var_def['type']
    var_val = var_def['default']
    var_desc = var_def.get('description', '')
    var_items = var_def.get('options', [])

    self.comparison_type = '=='

    self.search_property.init(
        name=var_name,
        type=var_type,
        value=var_val,
        description=var_desc,
        items=var_items,
    )

def get_variable_search_list(self, context) -> list[tuple[str, str, str]]:
    """
    Get the keys for `context.scene.search_class_name` in blender ENUM format
    """
    search_class = context.scene.entity_template[context.scene.search_class_name]
    return [(key, key, key) for key in search_class['variables'].keys()]

def get_entity_list(self, context) -> list[tuple[str, str, str]]:
    """
    Get the keys for `context.object.class_name` in blender ENUM format
    """
    return [(key, key, key) for key in context.scene.entity_template.keys()]

@bpy.app.handlers.persistent
def load_template(file) -> None:
    """
    Load entity template at the start of each session
    """
    bpy.context.scene.entity_template.init_dict()

# Setup Scene and object variables
def register():
    entity.register()
    operators.register()
    panels.register()

    # File IO
    bpy.types.Scene.entity_def_path = bpy.props.StringProperty(
        name = 'Godot entity definition path',
        description = 'The path of your Godot entity definition JSON',
        subtype = 'FILE_PATH',
    )
    bpy.types.Scene.btg_write_path = bpy.props.StringProperty(
        name = 'BTG import write-path',
        description = (
            'The path to write your BTG import JSON. You have to write '
            'this JSON in order to use the import script in Godot.'
        ),
        subtype = 'FILE_PATH',
    )

    # Entity definition
    bpy.types.Object.class_name = bpy.props.EnumProperty(
        items=get_entity_list,
        update=reset_class_definition,
        description='The Godot class of this object',
        default=0,
    )
    # Stores the class_name as a string rather than an index in the enum.
    # This is used when the enum is updated and we need to check if the class
    # order has changed.
    bpy.types.Object.class_name_backup = bpy.props.StringProperty()
    bpy.types.Object.class_definition = bpy.props.PointerProperty(type=entity.EntityDefinition)
    bpy.types.Scene.entity_template = bpy.props.PointerProperty(type=entity.EntityTemplate)

    # Property searching
    bpy.types.Scene.search_class_name = bpy.props.EnumProperty(
        name='Godot Entities',
        description='The Godot class to search for',
        items=get_entity_list,
        update=set_search_property,
        default=0,
    )
    bpy.types.Scene.search_type = bpy.props.EnumProperty(
        items=[
            ('class', 'Class name', 'Select all objects of this class'),
            ('var_val', 'Variable value', 'Select all objects with this variable value')
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
        items=get_variable_search_list,
        update=set_search_property,
        default=0,
    )
    bpy.types.Scene.search_property = bpy.props.PointerProperty(type=entity.EntityProperty)

def unregister():
    entity.unregister()
    operators.unregister()
    panels.unregister()

    # File IO
    del bpy.types.Scene.entity_def_path
    del bpy.types.Scene.btg_write_path

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

if __name__ == "__main__":
    register()