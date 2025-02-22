import bpy
import json
from mathutils import Vector
import enum

class PropTypes(enum.Enum):
    INT = 'mInt'
    FLOAT = 'mFloat'
    STRING = 'mString'
    BOOL = 'mBool'
    INT_VECTOR = 'mIntVector'
    FLOAT_VECTOR = 'mFloatVector'
    ENUM = 'mEnum'

# %% GUI Class
class Test(bpy.types.Panel):
    """
    Test
    """
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = 'Test'
    bl_category = 'Test'

    def draw(self, context):
        """
        Define the layout of the panel
        """
        layout = self.layout

        layout.label(text='Test')
        for prop in context.active_object.ent_def.properties:
            layout.label(text=prop.name)
            layout.prop(prop, prop.var_string, text='')


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

    def add(self, name: str, value: any) -> None:
        """
        Add var to `properties`

        Parameters
        ----------
        `name`: The Godot variable name
        `value`: The Godot variable value
        """
        prop = self.properties.add()
        prop.name = name

        prop_type = type(value)
        if prop_type == bool:
            prop.mBool = value
            prop.mType = PropTypes.BOOL.value
        elif prop_type == int:
            prop.mInt = value
            prop.mType = PropTypes.INT.value
        elif prop_type == float:
            prop.mFloat = value
            prop.mType = PropTypes.FLOAT.value
        elif prop_type in (tuple, Vector):
            if all([type(idx) == int for idx in value]):
                prop.mIntVector = value
                prop.mType = PropTypes.INT_VECTOR.value
            else:
                prop.mFloatVector = value
                prop.mType = PropTypes.FLOAT_VECTOR.value
        elif prop_type == list:
            prop.mEnumItems = json.dumps(value)
            prop.mType = PropTypes.ENUM.value
        else:
            prop.mString = value
            prop.mType = PropTypes.STRING.value

# %% Blender API Setup
def register():
    bpy.utils.register_class(Test)
    bpy.utils.register_class(EntityProperty)
    bpy.utils.register_class(EntityDefinition)

    bpy.types.Object.ent_def = bpy.props.PointerProperty(type=EntityDefinition)

def unregister():
    bpy.utils.unregister_class(Test)
    bpy.utils.unregister_class(EntityProperty)
    bpy.utils.unregister_class(EntityDefinition)

bl_info = {
    'name': 'Test',
    'blender': (2, 80, 0),
    'category': 'Object',
}

if __name__ == '__main__':
    register()
