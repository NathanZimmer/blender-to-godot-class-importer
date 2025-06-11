class_name PrimitiveCollisionShape3D extends CollisionShape3D

enum Primitives {BOX, SPHERE}

# BTG will populate this automatically
var mesh: Mesh

## TODO
func set_primitive(type: Primitives) -> void:
    match type:
        Primitives.BOX:
            shape = BoxShape3D.new()
            shape.size = mesh.get_aabb().size
        Primitives.SPHERE:
            shape = SphereShape3D.new()
            shape.radius = mesh.get_aabb().size.x / 2
