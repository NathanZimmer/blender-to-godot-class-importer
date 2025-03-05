## This is an example object for the BTG pipeline
class_name BTGExampleClass1 extends Node3D

@export var float_example: float = 0.5
@export var custom_float_example: float = 0.5


## Do something custom to one of our values.
## NOTE: function name matches "type" field in JSON
static func custom_float(value) -> float:
	return float(value) * -1
