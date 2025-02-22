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

entity_template = {'None': ''}

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

        class_name = active_object.class_name
        if class_name in ('None', ''):
            return

        for property in getattr(bpy.context.active_object, class_name).properties:
            entity_box.label(text=property.name)
            entity_box.prop(property, property.var_string, text='')



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
        # Putting this in a try-catch to prevent users from locking themselves out of loading
        # a new JSON
        global entity_template
        try:
            # Free variables from old def JSON
            del_class_defs()
            pass
        except:
            self.report({'ERROR'}, 'Could not free variables')

        try:
            self.read_template_json()
        except Exception:
            self.report(
                {'ERROR'}, f'Failed to load JSON file with exception:\n{traceback.format_exc()}'
            )
            return {'CANCELLED'}

        # Reinitialize after loading new entity template
        init()

        self.report({'DEBUG'}, f'{entity_template=}')
        self.report({'INFO'}, 'Loaded JSON!')
        return {'FINISHED'}

    @staticmethod
    def read_template_json() -> None:
        """
        Read json from scene var `entity_def_path` into scene var `entity_template_str`
        and global var `entity_template`
        """
        with open(bpy.context.scene.entity_def_path) as file:
            # Place 'None' at the first index for defaulting
            global entity_template
            entity_template = {'None': ''}
            entity_template |= json.load(file)

            # NOTE: Blender cannot store dict type objects, so this is a workaround
            # to preserve the dict between blender sessions.
            bpy.context.scene.entity_template_str = json.dumps(entity_template)


# %% Entity Def Classes
class EntityProperty(bpy.types.PropertyGroup):
    """
    List for Godot entity variables defined by the entity template
    """
    def get_prop_enum_items(self, _) -> list[tuple[str, str, str]]:
        """
        Return `self.mEnumItems` formatted for use with a Blender
        ENUM property
        """
        items = json.loads(self.mEnumItems)
        return [(str(val), str(val), str(val)) for val in items]

    @property
    def var_string(self) -> str:
        """
        TODO
        """
        return self.mType

    # Variable name and prop type
    name: bpy.props.StringProperty()  # type: ignore
    description: bpy.props.StringProperty()  # type: ignore
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
    mInt: bpy.props.IntProperty()  # type: ignore
    mFloat: bpy.props.FloatProperty()  # type: ignore
    mString: bpy.props.StringProperty()  # type: ignore
    mBool: bpy.props.BoolProperty()  # type: ignore
    mIntVector: bpy.props.IntVectorProperty()  # type: ignore
    mFloatVector: bpy.props.FloatVectorProperty()  # type: ignore
    mEnum: bpy.props.EnumProperty(items=get_prop_enum_items)  # type: ignore
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
        items: str = None
    ) -> None:
        """
        Add variable to `self.properties`

        Parameters
        ----------
        `name`: The Godot variable name
        `value`: The Godot variable value
        `type`: TODO
        `items`: TODO
        """
        prop = self.properties.add()
        prop.name = name
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

# %% Utility Functions
def init():
    """
    Called when a new entity template is read
    """
    global entity_template

    for class_name, class_def in entity_template.items():
        if class_name == 'None':
            continue

        setattr(
            bpy.types.Object,
            class_name,
            bpy.props.PointerProperty(type=EntityDefinition)
        )
        # Setup each object in the scene
        for object in bpy.context.scene.objects:
            entity_def = getattr(
                object,
                class_name,
            )
            for var_name, var_def in class_def.items():
                var_type, var_default, var_desc, var_items = var_def

                entity_def.add(
                    name=var_name,
                    type=var_type,
                    value=var_default,
                    description=var_desc,
                    items=var_items
                )

            object.instantiated = True

def init_new(scene) -> None:
    """
    TODO
    """
    for object in scene.objects:
        if not object.instantiated:
            for class_name, class_def in entity_template.items():
                if class_name == 'None':
                    continue

                entity_def = getattr(
                    object,
                    class_name,
                )
                for var_name, var_def in class_def.items():
                    var_type, var_default, var_desc, var_items = var_def

                    entity_def.add(
                        name=var_name,
                        type=var_type,
                        value=var_default,
                        description=var_desc,
                        items=var_items
                    )
            object.instantiated = True

def del_class_defs():
    """
    TODO
    """
    global entity_template
    for class_name in entity_template.keys():
        if class_name == 'None':
            continue
        for object in bpy.context.scene.objects:
            entity_def = getattr(
                    object,
                    class_name,
                )
            entity_def.properties.clear()

        delattr(bpy.types.Object, class_name)

@persistent
def load_template_from_string(file=None) -> None:
    """
    TODO
    """
    global entity_template
    entity_template = json.loads(bpy.context.scene.entity_template_str)

def get_entity_list(self=None, context=None) -> list[tuple[str, str, str]]:
    """
    Get the keys for `context.object.class_name` in blender ENUM format
    """
    global entity_template
    return [(key, key, key) for key in entity_template.keys()]

# %% Blender API Setup
def register():
    bpy.utils.register_class(BTGPanel)
    bpy.utils.register_class(EntityTemplateReader)
    # bpy.utils.register_class(EntityImportWriter)
    bpy.utils.register_class(EntityProperty)
    bpy.utils.register_class(EntityDefinition)

    if not load_template_from_string in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_template_from_string)
    if not init_new in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(init_new)

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
        name='Godot Entities',
        description='ENUM for each object\'s class selection',
        items=get_entity_list,
        default=0,
    )
    bpy.types.Object.instantiated = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.entity_template_str = bpy.props.StringProperty(
        name='Godot Entity JSON',
        description=(
            'Stores the entity definition for use between blender sessions. This is'
            'only read from on startup and only written to when a new def is loaded'
        ),
        default='{"None": ""}',
    )

def unregister():
    bpy.utils.unregister_class(BTGPanel)
    bpy.utils.unregister_class(EntityTemplateReader)
    # bpy.utils.unregister_class(EntityImportWriter)
    bpy.utils.unregister_class(EntityProperty)
    bpy.utils.unregister_class(EntityDefinition)

    if load_template_from_string in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_template_from_string)
    if init_new in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(init_new)

    # TODO: del variables

bl_info = {
    'name': 'Scratch',
    'blender': (2, 80, 0),
    'category': 'Object',
}

if __name__ == '__main__':
    register()