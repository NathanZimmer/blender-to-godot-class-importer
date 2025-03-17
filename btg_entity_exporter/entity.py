"""
BTG Entity classes. These classes contain the Godot Node/variables definitions
and functions for manipulating that data
"""

import bpy
import json
import enum


class PropTypes(enum.Enum):
    INT = 'mInt'
    FLOAT = 'mFloat'
    STRING = 'mString'
    BOOL = 'mBool'
    INT_VECTOR = 'mIntVector'
    FLOAT_VECTOR = 'mFloatVector'
    ENUM = 'mEnum'


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
    Represents a Godot variable. Wraps `bpy.props` objects
    for easier dynamic allocation and manipulation
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
        items: list[str] = None,
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

        match type:
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
        """
        Get variable described by `self.string_ref`
        """
        return getattr(self, self.mType)

    @value.setter
    def value(self, val: any) -> None:
        """
        Set variable described by `self.string_ref`
        """
        setattr(self, self.mType, val)

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
        ],
    )  # type: ignore

    # Supported value types
    # NOTE: We need to instantiate a var of each type because of API quirks
    mInt: bpy.props.IntProperty(
        name='int',
        override={'LIBRARY_OVERRIDABLE'},
    )  # type: ignore
    mFloat: bpy.props.FloatProperty(
        name='float',
        override={'LIBRARY_OVERRIDABLE'},
    )  # type: ignore
    mString: bpy.props.StringProperty(
        name='string',
        override={'LIBRARY_OVERRIDABLE'},
    )  # type: ignore
    mBool: bpy.props.BoolProperty(
        name='bool',
        override={'LIBRARY_OVERRIDABLE'},
    )  # type: ignore
    mIntVector: bpy.props.IntVectorProperty(
        name='Vector3i',
        override={'LIBRARY_OVERRIDABLE'},
    )  # type: ignore
    mFloatVector: bpy.props.FloatVectorProperty(
        name='Vector3',
        override={'LIBRARY_OVERRIDABLE'},
    )  # type: ignore
    mEnum: bpy.props.EnumProperty(
        name='enum',
        items=get_enum_items,
        override={'LIBRARY_OVERRIDABLE'},
    )  # type: ignore
    mEnumItems: bpy.props.StringProperty(
        default='{"None": ""}',
        override={'LIBRARY_OVERRIDABLE'},
    )  # type: ignore


class EntityDefinition(bpy.types.PropertyGroup):
    """
    Represents a Godot class/variables from the entity template JSON
    """

    # List of Godot variables
    properties: bpy.props.CollectionProperty(
        type=EntityProperty,
        override={'LIBRARY_OVERRIDABLE'},
    )  # type: ignore

    def add(
        self,
        name: str,
        value: any,
        type: str,
        description: str = '',
        items: list[str] = None,
    ) -> None:
        """
        Add a variable to this object's variable list.
        Variables are accessd by index.

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
        ```
        props: {
            name: {
                'type': ...,
                'value': ...,
                'description': ...,
                'items': ...,
            },
            ...
        }
        ```
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

    def __getitem__(self, key):
        return self.properties[key]


def register():
    """
    Blender API function
    """
    bpy.utils.register_class(EntityTemplate)
    bpy.utils.register_class(EntityProperty)
    bpy.utils.register_class(EntityDefinition)


def unregister():
    """
    Blender API function
    """
    bpy.utils.unregister_class(EntityTemplate)
    bpy.utils.unregister_class(EntityProperty)
    bpy.utils.unregister_class(EntityDefinition)
