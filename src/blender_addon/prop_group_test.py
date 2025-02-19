import bpy
from bpy.app.handlers import persistent
import json
import traceback
from mathutils import Vector
import enum

class PropTypes(enum.Enum):
    INT = 0
    FLOAT = 1
    STRING = 2
    BOOL = 3
    INT_VECTOR = 4
    FLOAT_VECTOR = 5

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
        for prop in context.scene.ent_def.mProperties:
            layout.label(text=prop.mName)
            layout.prop(prop, EntityDefinition.prop_indices[prop.mType], text='')


# %% Entity Def Classes
class PropertyList(bpy.types.PropertyGroup):
    """
    TODO
    """
    # Variable name from entity template and blender prop type
    mName: bpy.props.StringProperty()  # type: ignore
    mType: bpy.props.IntProperty()  # type: ignore

    # Supported value types
    mInt: bpy.props.IntProperty()  # type: ignore
    mFloat: bpy.props.FloatProperty()  # type: ignore
    mString: bpy.props.StringProperty()  # type: ignore
    mBool: bpy.props.BoolProperty()  # type: ignore
    mIntVector: bpy.props.IntVectorProperty()  # type: ignore
    mFloatVector: bpy.props.FloatVectorProperty()  # type: ignore
    # mEnum: bpy.props.EnumProperty()  # type: ignore  TODO


class EntityDefinition(bpy.types.PropertyGroup):
    """
    TODO
    """
    prop_indices = ['mInt', 'mFloat', 'mString', 'mBool', 'mIntVector', 'mFloatVector']
    mProperties: bpy.props.CollectionProperty(type=PropertyList)  # type: ignore

    def clear(self):
        self.mProperties.clear()

    def __getitem__(self, key):
        # TODO: remove for-loop
        for prop in self.mProperties:
            if prop.mName == key:
                return prop[self.prop_indices[prop.mType]]


    def __setitem__(self, key, value):
        # TODO: remove for-loop
        for existing_prop in self.mProperties:
            if existing_prop.mName == key:
                prop = existing_prop
                break
        else:
            prop = self.mProperties.add()
            prop.mName = key

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
        elif prop_type in (tuple, list, Vector):
            if all([type(idx) == int for idx in value]):
                prop.mIntVector = value
                prop.mType = PropTypes.INT_VECTOR.value
            else:
                prop.mFloatVector = value
                prop.mType = PropTypes.FLOAT_VECTOR.value
        else:
            prop.mString = value
            prop.mType = PropTypes.STRING.value


# %% Blender API Setup
def register():
    bpy.utils.register_class(Test)
    bpy.utils.register_class(PropertyList)
    bpy.utils.register_class(EntityDefinition)

    bpy.types.Scene.ent_def = bpy.props.PointerProperty(type=EntityDefinition)

def unregister():
    bpy.utils.unregister_class(Test)
    bpy.utils.unregister_class(PropertyList)
    bpy.utils.unregister_class(EntityDefinition)

bl_info = {
    'name': 'Test',
    'blender': (2, 80, 0),
    'category': 'Object',
}

if __name__ == '__main__':
    register()
# %%
