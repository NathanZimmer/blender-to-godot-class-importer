"""
Blender-to-Godot entity exporter. This module reads from an entity template
JSON and writes an entity definition JSON. Install this in Blender as an addon.
"""
import bpy
from bpy.app.handlers import persistent
import json
import traceback
import numpy as np
import enum

class PropTypes(enum.Enum):
    INT = 'mInt'
    FLOAT = 'mFloat'
    STRING = 'mString'
    BOOL = 'mBool'
    INT_VECTOR = 'mIntVector'
    FLOAT_VECTOR = 'mFloatVector'
    ENUM = 'mEnum'


# %% GUI Classes
class BTGPanel(bpy.types.Panel):
    """
    Settings panel for the Blender to Godot pipeline
    """
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = 'Blender to Godot Pipeline'
    bl_category = 'Blender To Godot'

    def draw(self, context):
        """
        Define the layout of the panel
        """
        layout = self.layout
        active_object = context.active_object
        scene_props = context.scene.bl_rna.properties

        # Import and export UI
        layout.label(text='Import and Export')
        import_export_box = layout.box()
        import_export_box.label(text=scene_props['entity_def_path'].name)
        import_export_box.prop(context.scene, 'entity_def_path', text='')
        import_export_box.operator('json.read')
        import_export_box.label(text=scene_props['btg_write_path'].name)
        import_export_box.prop(context.scene, 'btg_write_path', text='')
        import_export_box.operator('json.write')

        # Search UI
        layout.label(text='Select Objects')
        misc = layout.box()
        misc.operator('select_popup.open')

        # Don't show properties if there is no object selected
        if active_object is None:
            return

        # Entity properties GUI
        layout.label(text='Entity Properties')
        entity_box = layout.box()
        entity_box.label(text='Godot Class')
        entity_box.prop(active_object, 'class_name', text='')
        # Don't show properties if there are none
        class_name = active_object.class_name
        if class_name in ('None', ''):
            return
        # Display class properties
        for property in active_object.class_definition:
            entity_box.label(text=f'{property.name} ({property.godot_type})')
            entity_box.prop(property, property.string_ref, text='')


class SelectionPopup(bpy.types.Operator):
    """
    Search for objects in the scene based on class name or class variable value
    """
    bl_idname = "select_popup.open"
    bl_label = "Find objects by..."

    def execute(self, context):
        """
        Use search_ scene variables to select objects with the specified entity values
        """
        search_class = context.scene.search_class_name

        # Search for matching vars
        if context.scene.search_type == 'var_val' and search_class != 'None':
            search_var_name = context.scene.search_var_name
            search_property = context.scene.search_property

            if search_var_name == '':
                self.report({'WARNING'}, 'No search variable selected.')
                return {'CANCELLED'}

            for object in context.scene.objects:
                if object.class_name != search_class:
                    continue

                value = object.class_definition.get_properties()[search_var_name]['value']
                object.select_set(
                    object.class_name == search_class
                    and SelectionPopup.compare(value, search_property.value, context.scene.comparison_type)
                )
        # Search for matching classes
        else:
            for object in context.scene.objects:
                object.select_set(object.class_name == search_class)

        if len(context.selected_objects) > 0 and context.active_object not in context.selected_objects:
            context.view_layer.objects.active = context.selected_objects[0]

        if len(context.selected_objects) == 0:
            self.report({'INFO'}, 'No objects found.')
        else:
            self.report({'INFO'}, 'Objects selected!')

        return {'FINISHED'}

    @staticmethod
    def close(x: any, y: any, delta: float = 1.e-8) -> bool:
        """
        Check if vars `x` and `y` are within `delta` distance
        """
        # If string, do regular equality
        if isinstance(x, str) or isinstance(y, str):
            return x == y

        return np.allclose(x, y, atol=delta)

    @staticmethod
    def compare(x: any, y: any, comp_type: str) -> bool:
        """
        Compares inputs `x` and `y` based on `comp_type`

        parameters
        ----------
        `x`, `y`: Inputs to compare
        `comp_type`: Method of comparison. Valid input: `'<', '<=', '==', '>', '>='`

        returns
        -------
        `result`: result of `x` compared to `y` by `comp_type`
        """
        match (comp_type):
            case '<':
                return x < y
            case '<=':
                return x <= y
            case '==':
                return SelectionPopup.close(x, y)
            case '>':
                return x > y
            case '>=':
                return x >= y
            case '_':
                return SelectionPopup.close(x, y)

    def invoke(self, context, event):
        """
        Invoke popup
        """
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        """
        Define the layout of the sub-panel
        """
        layout = self.layout

        layout.label(text='Search by...')
        layout.prop(context.scene, 'search_type', text='')

        layout.label(text='Parameters')
        box = layout.box()
        box.prop(context.scene, 'search_class_name', text='')

        if context.scene.search_class_name == 'None':
            return

        if context.scene.search_type == 'var_val':
            box.prop(context.scene, 'search_var_name', text='')

            search_property = context.scene.search_property
            # Types that we want to show the expanded set of comparison options for
            expanded_compare_types =  (
                PropTypes.INT.value,
                PropTypes.FLOAT.value,
                PropTypes.FLOAT_VECTOR.value,
                PropTypes.INT_VECTOR.value
            )
            if search_property.string_ref in expanded_compare_types:
                box.prop(context.scene, 'comparison_type', text='')

            box.prop(search_property, search_property.string_ref, text='')


# %% Operator Classes
class EntityTemplateReader(bpy.types.Operator):
    """
    Read Godot entity template JSON and save to global `entity_template` dict
    """
    bl_idname = 'json.read'
    bl_label = 'Read entity JSON'

    def execute(self, context):
        """
        Read entity template from JSON and initialize values for all scene objects
        """
        try:
            self.read_template_json()
        except Exception:
            self.report(
                {'ERROR'}, f'Failed to load JSON file with exception:\n{traceback.format_exc()}'
            )
            return {'CANCELLED'}

        # Clear old defs and refresh updated defs
        refresh_class_definitions()

        self.report({'DEBUG'}, f'{context.scene.entity_template=}')
        self.report({'INFO'}, 'Loaded JSON!')
        return {'FINISHED'}

    @staticmethod
    def read_template_json() -> None:
        """
        Read json from `scene.entity_def_path` into `scene.entity_template`
        """
        entity_def_path = bpy.context.scene.entity_def_path
        if entity_def_path[:2] == '//':
            entity_def_path = bpy.path.abspath('//') + entity_def_path[2:]
        with open(entity_def_path) as entity_json:
            # Place 'None' at the first index for defaulting
            bpy.context.scene.entity_template.reset({'None': ''} | json.load(entity_json))


class EntityImportWriter(bpy.types.Operator):
    """
    Write BTG import JSON from entity defintions
    """
    bl_idname = 'json.write'
    bl_label = 'Write BTG import JSON'

    def execute(self, context):
        """
        Write entity definitions to Godot import JSON
        """
        json_types = (int, str, bool, float)  # Values that can be translated to JSON format

        btg_json = {
            # Convert to Godot naming standards
            object.name.replace('.', '_'): {
                'class': object.class_name,
                'variables': {
                    prop.name: {
                        'type': prop.godot_type,
                        'value': (
                            prop.value if type(prop.value) in json_types
                            else str(prop.value[0:])  # Convert non-JSON vartypes to string
                        )
                    }
                    for prop in object.class_definition
                }
            }
            for object in context.scene.objects if object.class_name != 'None'
        }

        try:
            btg_write_path = bpy.context.scene.btg_write_path
            if btg_write_path[:2] == '//':
                btg_write_path = bpy.path.abspath('//') + btg_write_path[2:]
            with open(btg_write_path, 'w+') as file:
                json.dump(btg_json, file)

            self.report({'DEBUG'}, f'{btg_json=}')
            self.report({'INFO'}, 'Wrote JSON!')
            return {'FINISHED'}
        except Exception:
            self.report(
                {'ERROR'}, f'Failed to write JSON file with exception:\n{traceback.format_exc()}'
            )
            return {'CANCELLED'}

# %% Entity Classes
class EntityTemplate(bpy.types.PropertyGroup):
    """
    Wrapper for entity template JSON file
    """
    template = {}
    template_str: bpy.props.StringProperty(default='{"None": ""}')  # type: ignore

    def init_dict(self) -> None:
        """
        Repopulate template dict from string after Blender restart
        """
        self.template.clear()
        self.template |= json.loads(self.template_str)

    def reset(self, template: dict) -> None:
        """
        Reset this object with a new template JSON
        """
        self.template.clear()
        self.template |= template

        # NOTE: Blender cannot store dict type objects, so this is a workaround
        # to preserve the dict between blender sessions.
        self.template_str = json.dumps(template)

    def keys(self) -> None:
        return self.template.keys()

    def items(self) -> None:
        return self.template.items()

    def __getitem__(self, key) -> any:
        return self.template[key]

    def __contains__(self, key):
        return key in self.template


class EntityProperty(bpy.types.PropertyGroup):
    """
    List for Godot entity variables
    """
    def get_enum_items(self, _=None) -> list[tuple[str, str, str]]:
        """
        Return `self.mEnumItems` formatted for use with a Blender
        ENUM property
        """
        items = json.loads(self.mEnumItems)
        return [(str(val), str(val), str(val)) for val in items]

    def init(
        self,
        name: str,
        value: any,
        type: str,
        description: str = '',
        items: list[str] = []
    ) -> None:
        """
        Initialize object
        NOTE: Needs to be called manually because `__init__` is not called by the
        Blender API

        Parameters
        ----------
        `name`: Name of the corresponding Godot variable

        `value`: Value of the corresponding Godot variable

        `type`: Godot type of the corresponding variable

        `description`: Optional, the description of this variable.
        NOTE: currently unused

        `items`: Optional, fill this param if `type == 'enum'`
        """
        self.name = name
        self.godot_type = type
        self.description = description

        match(type):
            case 'bool':
                self.mBool = value
                self.mType = PropTypes.BOOL.value
            case 'int':
                self.mInt = value
                self.mType = PropTypes.INT.value
            case 'float':
                self.mFloat = value
                self.mType = PropTypes.FLOAT.value
            case 'Vector3':
                self.mFloatVector = value
                self.mType = PropTypes.FLOAT_VECTOR.value
            case 'Vector3i':
                self.mIntVector = value
                self.mType = PropTypes.INT_VECTOR.value
            case 'enum':
                self.mEnumItems = json.dumps(items)
                self.mEnum = value
                self.mType = PropTypes.ENUM.value
            case _:
                self.mString = value
                self.mType = PropTypes.STRING.value

    @property
    def string_ref(self) -> str:
        """
        Return string name of this property's value for `layout.prop`
        GUI displaying
        """
        return self.mType

    @property
    def value(self) -> any:
        return self[self.mType]

    @value.setter
    def value(self, val: any) -> None:
        self[self.mType] = val

    # Variable name and prop type
    name: bpy.props.StringProperty()  # type: ignore
    # TODO: Find a way to override the tooltip to show each property's desc
    description: bpy.props.StringProperty()  # type: ignore
    godot_type: bpy.props.StringProperty()  # type: ignore

    mType: bpy.props.EnumProperty(
        items=[
            ('mInt', 'mInt', 'mInt'),
            ('mFloat', 'mFloat', 'mFloat'),
            ('mString', 'mString', 'mString'),
            ('mBool', 'mBool', 'mBool'),
            ('mIntVector', 'mIntVector', 'mIntVector'),
            ('mFloatVector', 'mFloatVector', 'mFloatVector'),
            ('mEnum', 'mEnum', 'mEnum'),
        ]
    )  # type: ignore

    # Supported value types
    mInt: bpy.props.IntProperty(name='int')  # type: ignore
    mFloat: bpy.props.FloatProperty(name='float')  # type: ignore
    mString: bpy.props.StringProperty(name='string')  # type: ignore
    mBool: bpy.props.BoolProperty(name='bool')  # type: ignore
    mIntVector: bpy.props.IntVectorProperty(name='Vector3i')  # type: ignore
    mFloatVector: bpy.props.FloatVectorProperty(name='Vector3')  # type: ignore
    mEnum: bpy.props.EnumProperty(name='enum', items=get_enum_items)  # type: ignore
    mEnumItems: bpy.props.StringProperty(default='{"None": ""}')  # type: ignore


class EntityDefinition(bpy.types.PropertyGroup):
    """
    Represents a Godot class with variables defined in the entity template
    """
    properties: bpy.props.CollectionProperty(type=EntityProperty)  # type: ignore

    def add(
        self,
        name: str,
        value: any,
        type: str,
        description: str = '',
        items: list[str] = []
    ) -> None:
        """
        Add variable to `self.properties`

        Parameters
        ----------
        `name`: Name of the corresponding Godot variable

        `value`: Value of the corresponding Godot variable

        `type`: Godot type of the corresponding variable

        `description`: Optional, the description of this variable.
        NOTE: currently unused

        `items`: Optional, fill this param if `type == 'enum'`
        """
        prop = self.properties.add()
        prop.init(name, value, type, description, items)

    def clear(self) -> None:
        """
        Deletes this entity's variables
        """
        self.properties.clear()

    def get_properties(self) -> dict:
        """
        Get dictionary representation of this object's properties

        Returns
        -------
        `props`: dictionary with `prop.name` of each property as key and
        `'type', 'value', 'description', 'items'` as sub-dictionary keys
        """
        return {
            prop.name: {
                'type': prop.godot_type,
                'value': prop.value,
                'description': prop.description,
                'items': prop.get_enum_items(),
            }
            for prop in self.properties
        }

    def __iter__(self):
        return self.properties.__iter__()


# %% Utility Functions
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

    for var_name, var_def in class_def.items():
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

def refresh_class_definitions() -> None:
    """
    Compare `object.class_definition` values to `scene.entity_template`.
    Check if:
    * class was removed
    * class order was changed
    * class variables were reordered/changed
    """
    scene = bpy.context.scene

    for object in bpy.context.scene.objects:
        # If object is None, it has no vars to clear
        if object.class_name == 'None':
            continue

        # If class was removed from template, clear its definition
        if object.class_name_backup not in scene.entity_template:
            object.class_name = 'None'
            object.class_definition.clear()
            continue

        # If class def was updated, re-assign values from previous def
        # Grab old variables
        old_props = object.class_definition.get_properties()
        # Reset to backup in-case class definition order has changed
        object.class_name = object.class_name_backup
        # refill common vars between previous and current template iterations
        for prop in object.class_definition:
            name = prop.name
            type = prop.godot_type
            if name in old_props and type == old_props[name]['type']:
                prop.value = old_props[name]['value']

def set_search_property(self, context) -> None:
    """
    Set the Scene search property based on `context.scene.search_class_name` and
    `context.scene.search_var_name`
    """
    class_name = context.scene.search_class_name
    var_name = context.scene.search_var_name
    var_type, var_val, var_desc, var_items = context.scene.entity_template[class_name][var_name]

    context.scene.comparison_type = '=='

    context.scene.search_property.init(
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
    return [(key, key, key) for key in search_class.keys()]

def get_entity_list(self, context) -> list[tuple[str, str, str]]:
    """
    Get the keys for `context.object.class_name` in blender ENUM format
    """
    return [(key, key, key) for key in context.scene.entity_template.keys()]

@persistent
def load_template(file) -> None:
    """
    Load entity template at the start of each session
    """
    bpy.context.scene.entity_template.init_dict()

# %% Blender API Setup
def register():
    bpy.utils.register_class(BTGPanel)
    bpy.utils.register_class(SelectionPopup)
    bpy.utils.register_class(EntityTemplateReader)
    bpy.utils.register_class(EntityImportWriter)
    bpy.utils.register_class(EntityTemplate)
    bpy.utils.register_class(EntityProperty)
    bpy.utils.register_class(EntityDefinition)

    if not load_template in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_template)

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
    bpy.types.Object.class_definition = bpy.props.PointerProperty(type=EntityDefinition)
    bpy.types.Scene.entity_template = bpy.props.PointerProperty(type=EntityTemplate)

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
    bpy.types.Scene.search_property = bpy.props.PointerProperty(type=EntityProperty)

def unregister():
    bpy.utils.unregister_class(BTGPanel)
    bpy.utils.unregister_class(EntityTemplateReader)
    bpy.utils.unregister_class(EntityImportWriter)
    bpy.utils.register_class(EntityTemplate)
    bpy.utils.unregister_class(EntityProperty)
    bpy.utils.unregister_class(EntityDefinition)

    if load_template in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_template)

    # File IO
    del bpy.types.Scene.entity_def_path
    del bpy.types.Scene.btg_write_path

    # Entity definition
    del bpy.types.Object.class_name
    del bpy.types.Object.class_name_backup
    for object in bpy.context.scene.objects:
        object.class_definition.clear()
    del bpy.types.Object.class_definition
    del bpy.types.Scene.entity_templat

    # Property searching
    del bpy.types.Scene.search_class_name
    del bpy.types.Scene.search_type
    del bpy.types.Scene.comparison_type
    del bpy.types.Scene.search_var_name
    del bpy.types.Scene.search_property


bl_info = {
    'name': 'Nathan\'s Blender To Godot (BTG) Pipeline',
    'blender': (2, 80, 0),
    'category': 'Object',
}

if __name__ == '__main__':
    register()