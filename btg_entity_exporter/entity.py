"""
BTG Entity classes. These classes contain the Godot Node/variables definitions
and functions for manipulating that data
"""

import bpy
import json
import enum


class PropTypes(enum.Enum):
    INT = 'm_int'
    FLOAT = 'm_float'
    STRING = 'm_string'
    BOOL = 'm_bool'
    INT_VECTOR = 'm_int_vector'
    FLOAT_VECTOR = 'm_float_vector'
    ENUM = 'm_emum'


# class GodotPropTypes(enum.Enum):
#     BOOL = 'bool'
#     INT = 'int'
#     FLOAT = 'float'
#     VECTOR_3 = 'Vector3'
#     VECTOR_3 = 'Vector3'
#     VECTOR_2 = 'Vector2'
#     VECTOR_2_I = 'Vector2i'
#     ENUM = 'enum'

class EntityTemplate(bpy.types.PropertyGroup):
    """
    Wrapper for entity template JSON file
    """

    m_template = {}
    m_template_str: bpy.props.StringProperty(default='{"None": ""}')  # type: ignore

    def init_dict(self) -> None:
        """
        Repopulate template dict from string after Blender restart
        """
        self.m_template.clear()
        self.m_template |= json.loads(self.m_template_str)

    def reset(self, template: dict) -> None:
        """
        Reset this object with a new template JSON
        """
        self.m_template.clear()
        self.m_template |= template

        # Blender cannot store dict type objects, so this is a workaround
        # to preserve the dict between blender sessions.
        self.m_template_str = json.dumps(template)

    def keys(self) -> None:
        return self.m_template.keys()

    def items(self) -> None:
        return self.m_template.items()

    def __getitem__(self, key) -> any:
        return self.m_template[key]

    def __contains__(self, key):
        return key in self.m_template


class EntityProperty(bpy.types.PropertyGroup):
    """
    Represents a Godot variable. Wraps `bpy.props` objects
    for easier dynamic allocation and manipulation
    """

    def get_enum_items(self, _=None) -> list[tuple[str, str, str]]:
        """
        Return `self.m_enum_items` formatted for use with a Blender
        ENUM property
        """
        items = json.loads(self.m_enum_items)
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
        Currently unused

        `items`: Optional, the enum items if `type == 'enum'`
        """
        self.name = name
        self.godot_type = type
        self.description = description

        match type:
            case 'bool':
                self.m_bool = value
                self.m_type = PropTypes.BOOL.value
            case 'int':
                self.m_int = value
                self.m_type = PropTypes.INT.value
            case 'float':
                self.m_float = value
                self.m_type = PropTypes.FLOAT.value
            case 'Vector3':
                self.m_float_vector.size = 3
                self.m_float_vector = value
                self.m_type = PropTypes.FLOAT_VECTOR.value
            case 'Vector3i':
                self.m_int_vector.size = 3
                self.m_int_vector = value
                self.m_type = PropTypes.INT_VECTOR.value
            case 'Vector2':
                self.m_float_vector.size = 2
                self.m_float_vector = value
                self.m_type = PropTypes.FLOAT_VECTOR.value
            case 'Vector2i':
                self.m_int_vector.size = 2
                self.m_int_vector = value
                self.m_type = PropTypes.INT_VECTOR.value
            case 'enum':
                self.m_enum_items = json.dumps(items)
                self.m_enum = value
                self.m_type = PropTypes.ENUM.value
            case _:
                self.m_string = value
                self.m_type = PropTypes.STRING.value

    @property
    def string_ref(self) -> str:
        """
        Return string name of this property's value for `layout.prop`
        GUI displaying
        """
        return self.m_type

    @property
    def value(self) -> any:
        """
        Get variable described by `self.string_ref`
        """
        return getattr(self, self.m_type)

    @value.setter
    def value(self, val: any) -> None:
        """
        Set variable described by `self.string_ref`
        """
        setattr(self, self.m_type, val)

    # Variable name and prop type
    name: bpy.props.StringProperty()  # type: ignore
    # TODO: Find a way to override the tooltip to show each property's desc
    description: bpy.props.StringProperty()  # type: ignore
    godot_type: bpy.props.StringProperty()  # type: ignore

    m_type: bpy.props.EnumProperty(
        items=[
            ('m_int', 'm_int', 'm_int'),
            ('m_float', 'm_float', 'm_float'),
            ('m_string', 'm_string', 'm_string'),
            ('m_bool', 'm_bool', 'm_bool'),
            ('m_int_vector', 'm_int_vector', 'm_int_vector'),
            ('m_float_vector', 'm_float_vector', 'm_float_vector'),
            ('m_emum', 'm_emum', 'm_emum'),
        ],
    )  # type: ignore

    # Supported value types
    # NOTE: We need to instantiate a var of each type because of API quirks
    # NOTE: Blender does not allow bpy.prop variables to be named with "_", so we
    # are using "m_" to denote private instead
    m_int: bpy.props.IntProperty(
        name='int',
        override={'LIBRARY_OVERRIDABLE'},
    )  # type: ignore
    m_float: bpy.props.FloatProperty(
        name='float',
        override={'LIBRARY_OVERRIDABLE'},
    )  # type: ignore
    m_string: bpy.props.StringProperty(
        name='string',
        override={'LIBRARY_OVERRIDABLE'},
    )  # type: ignore
    m_bool: bpy.props.BoolProperty(
        name='bool',
        override={'LIBRARY_OVERRIDABLE'},
    )  # type: ignore
    m_int_vector: bpy.props.IntVectorProperty(
        name='Vector3i',
        override={'LIBRARY_OVERRIDABLE'},
    )  # type: ignore
    m_float_vector: bpy.props.FloatVectorProperty(
        name='Vector3',
        override={'LIBRARY_OVERRIDABLE'},
    )  # type: ignore
    m_enum: bpy.props.EnumProperty(
        name='enum',
        items=get_enum_items,
        override={'LIBRARY_OVERRIDABLE'},
    )  # type: ignore
    m_enum_items: bpy.props.StringProperty(
        default='{"None": ""}',
        override={'LIBRARY_OVERRIDABLE'},
    )  # type: ignore


class EntityDefinition(bpy.types.PropertyGroup):
    """
    Represents a Godot class and its variables from the entity template JSON
    """

    # List of Godot variables
    m_properties: bpy.props.CollectionProperty(
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

        `description`: Optional, the description of this variable. Currently unused

        `items`: Optional, fill this param if `type == 'enum'`
        """
        prop = self.m_properties.add()
        prop.init(name, value, type, description, items)

    def clear(self) -> None:
        """
        Deletes this entity's variables
        """
        self.m_properties.clear()

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
            for prop in self.m_properties
        }

    def __iter__(self):
        return self.m_properties.__iter__()

    def __getitem__(self, key):
        return self.m_properties[key]


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
