## This is an example object for the BTG pipeline
class_name BTGExampleClass0 extends Node3D

enum ExampleEnum {OPTION_1, OPTION_2, OPTION_3}

@export var string_example: String = "string example"
@export var int_example: int = 1
@export var vector_example: Vector3 = Vector3(1, 2, 3)
@export var enum_example: ExampleEnum = ExampleEnum.OPTION_1