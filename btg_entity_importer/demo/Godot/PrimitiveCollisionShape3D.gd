class_name PrimitiveCollisionShape3D extends CollisionShape3D

enum Primitives {BOX, SPHERE}

@export var _primitive_type: Primitives

# BTG will populate this automatically
var mesh: Mesh :
    set(value):
        match _primitive_type:
            Primitives.BOX:
                shape = BoxShape3D.new()
                shape.size = value.get_aabb().size
            Primitives.SPHERE:
                shape = SphereShape3D.new()
                shape.radius = value.get_aabb().size.length()
