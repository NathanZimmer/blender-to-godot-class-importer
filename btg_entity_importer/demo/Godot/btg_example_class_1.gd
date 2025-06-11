## This is an example object for the BTG pipeline
class_name BTGExampleClass1 extends Node3D

@export var float_example: float = 0.5
@export var custom_float_example: float = 0.5


# TODO
func custom_float(value: float) -> void:
    custom_float_example = value * -1
