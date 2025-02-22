import bpy
from bpy.app.handlers import persistent
import json
import traceback
from mathutils import Vector
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

        layout.label(text='Import and Export')
        import_export_box = layout.box()
        import_export_box.label(text=scene_props['entity_def_path'].name)
        import_export_box.prop(context.scene, 'entity_def_path', text='')
        import_export_box.operator('json.read')
        # import_export_box.label(text=scene_props['btg_write_path'].name)
        # import_export_box.prop(context.scene, 'btg_write_path', text='')
        # import_export_box.operator('json.write')

        # Don't show properties if there is no object selected
        if active_object is None:
            return

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
        Read json from scene var `entity_def_path` into scene var `entity_template_str`
        and global var `entity_template`
        """
        with open(bpy.context.scene.entity_def_path) as entity_json:
            # Place 'None' at the first index for defaulting
            bpy.context.scene.entity_template.reset({'None': ''} | json.load(entity_json))


class EntityTemplate(bpy.types.PropertyGroup):
    """
    Wrapper for entity template JSON file
    """
    template = {}
    template_str: bpy.props.StringProperty(default='{"None": ""}')  # type: ignore

    def init_dict(self) -> None:
        """
        Repopulate template dict after Blender restart
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


# %% Entity Def Classes
class EntityProperty(bpy.types.PropertyGroup):
    """
    List for Godot entity variables
    """
    def get_prop_enum_items(self, _) -> list[tuple[str, str, str]]:
        """
        Return `self.mEnumItems` formatted for use with a Blender
        ENUM property
        """
        items = json.loads(self.mEnumItems)
        return [(str(val), str(val), str(val)) for val in items]

    @property
    def string_ref(self) -> str:
        """
        Return string name of this property's value for `layout.prop`
        GUI displaying
        """
        return self.mType

    # Variable name and prop type
    name: bpy.props.StringProperty()  # type: ignore
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
    mEnum: bpy.props.EnumProperty(name='enum', items=get_prop_enum_items)  # type: ignore
    mEnumItems: bpy.props.StringProperty()  # type: ignore


class EntityDefinition(bpy.types.PropertyGroup):
    """
    Represents a Godot class with variables defined by the entity template
    """
    properties: bpy.props.CollectionProperty(type=EntityProperty)  # type: ignore

    def add(
        self,
        name: str,
        value: any,
        type: str,
        description: str,
        items: list[str] = None
    ) -> None:
        """
        Add variable to `self.properties`

        Parameters
        ----------
        `name`: The Godot variable name
        `value`: The Godot variable value
        `type`: The Godot type of the variable.
        `items`: the items for an ENUM property
        """
        prop = self.properties.add()
        prop.name = name
        prop.godot_type = type
        prop.description = description

        match(type):
            case 'bool':
                prop.mBool = value
                prop.mType = PropTypes.BOOL.value
            case 'int':
                prop.mInt = value
                prop.mType = PropTypes.INT.value
            case 'float':
                prop.mFloat = value
                prop.mType = PropTypes.FLOAT.value
            case 'Vector3':
                prop.mFloatVector = value
                prop.mType = PropTypes.FLOAT_VECTOR.value
            case 'Vector3i':
                prop.mIntVector = value
                prop.mType = PropTypes.INT_VECTOR.value
            case 'enum':
                prop.mEnumItems = json.dumps(items)
                prop.mEnum = value
                prop.mType = PropTypes.ENUM.value
            case _:
                prop.mString = value
                prop.mType = PropTypes.STRING.value

    def clear(self) -> None:
        """
        Clears this entity
        """
        self.properties.clear()

    def get_properties(self) -> dict:
        """
        Get dictionary representation of this object's properties

        Returns
        -------
        `props`: dictionary with `prop.name` as key and `'type', 'value', 'description', 'items'`
        as sub-dictionary keys
        """
        return {
            prop.name: {
                'type': prop.godot_type,
                'value': prop[prop.string_ref],
                'description': prop.description,
                'items': '' if prop.mEnumItems == '' else json.loads(prop.mEnumItems)
            }
            for prop in self.properties
        }

    def __iter__(self):
        return self.properties.__iter__()


# %% Utility Functions
def init(self, context) -> None:
    """
    Update object variables for new `self.class_name`
    """
    self.class_definition.clear()
    self.class_name_backup = self.class_name

    if self.class_name == 'None':
        return

    class_def = context.scene.entity_template[self.class_name]

    for var_name, var_def in class_def.items():
        var_type, var_default, var_desc, var_items = var_def

        self.class_definition.add(
            name=var_name,
            type=var_type,
            value=var_default,
            description=var_desc,
            items=var_items
        )

def refresh_class_definitions():
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
        old_props = object.class_definition.get_properties()
        # Reset to backup in-case class definition order has changed
        object.class_name = object.class_name_backup
        # Reset any common vars between previous and current template iterations
        for property in object.class_definition:
            name = property.name
            type = property.godot_type
            if name in old_props and type == old_props[name]['type']:
                property[property.string_ref] = old_props[name]['value']

@persistent
def load_template(file=None) -> None:
    """
    Load entity template at the start of each session
    """
    bpy.context.scene.entity_template.init_dict()

def get_entity_list(self, context) -> list[tuple[str, str, str]]:
    """
    Get the keys for `context.object.class_name` in blender ENUM format
    """
    return [(key, key, key) for key in context.scene.entity_template.keys()]

# %% Blender API Setup
def register():
    bpy.utils.register_class(BTGPanel)
    bpy.utils.register_class(EntityTemplateReader)
    # bpy.utils.register_class(EntityImportWriter)
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
        update=init,
        description='The Godot class of this object',
        default=0,
    )
    # Stores the class_name as a string rather than an index in the enum.
    # This is used when the enum is updated and we need to check if the class
    # order has changed.
    bpy.types.Object.class_name_backup = bpy.props.StringProperty()
    bpy.types.Object.class_definition = bpy.props.PointerProperty(type=EntityDefinition)
    bpy.types.Scene.entity_template = bpy.props.PointerProperty(type=EntityTemplate)

def unregister():
    bpy.utils.unregister_class(BTGPanel)
    bpy.utils.unregister_class(EntityTemplateReader)
    # bpy.utils.unregister_class(EntityImportWriter)
    bpy.utils.register_class(EntityTemplate)
    bpy.utils.unregister_class(EntityProperty)
    bpy.utils.unregister_class(EntityDefinition)

    if load_template in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_template)

    # TODO: del variables

bl_info = {
    'name': 'Scratch',
    'blender': (2, 80, 0),
    'category': 'Object',
}

if __name__ == '__main__':
    register()