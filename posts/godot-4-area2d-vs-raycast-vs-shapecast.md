---
title: Area2D vs RayCast2D vs ShapeCast2D for melee attacks in Godot 4 — which and when
description: A practical Godot 4 comparison of the three ways to detect a sword swing, punch or bullet hit — Area2D, RayCast2D and ShapeCast2D — with the one-frame delay nobody warns you about and a clear rule for picking.
slug: godot-4-area2d-vs-raycast-vs-shapecast
date: 2026-09-23
product_name: Saltmire Hitbox
product_url: https://saltmire.itch.io/saltmire-hitbox
---

You press attack, the sword animation plays, and now the game has to answer one
question: *what did that swing touch?* Godot 4 gives you three nodes that can answer it —
`Area2D`, `RayCast2D` and `ShapeCast2D` — and every tutorial seems to pick a different
one. They are not interchangeable. Each one answers the question at a different *time*
and with a different *shape*, and that is the whole decision.

## Area2D: an overlap you listen to

An `Area2D` with a `CollisionShape2D` child sits in the world and emits signals when
other areas or bodies enter it. For melee, you enable it during the active frames of the
attack and listen for `area_entered`.

```gdscript
extends Area2D # the sword's hitbox

@export var damage := 10

func _ready() -> void:
	monitoring = false
	area_entered.connect(_on_area_entered)

func start_swing() -> void:
	set_deferred("monitoring", true)

func end_swing() -> void:
	set_deferred("monitoring", false)

func _on_area_entered(area: Area2D) -> void:
	if area.has_method("take_hit"):
		area.take_hit(damage)
```

Strengths: it's visual (you size the shape in the editor), it tracks lingering hitboxes
for free (a fire patch, a spinning blade), and it plays nicely with collision layers.

The catch everyone hits eventually: **Area2D results lag by one physics frame.** Overlaps
are computed during the physics step, so if you turn `monitoring` on and immediately call
`get_overlapping_areas()` in the same frame, you get an empty array. For a 3-frame jab at
60 FPS, losing one frame is a third of your active window. That's the source of the
classic "my attack only hits sometimes" bug.

## RayCast2D: a line, checked right now

A `RayCast2D` tests a single line from its origin to `target_position`. Its killer
feature for combat is `force_raycast_update()` — it queries the physics space
**immediately**, in the same frame.

```gdscript
@onready var ray: RayCast2D = $RayCast2D

func fire_hitscan(direction: Vector2, reach: float) -> void:
	ray.target_position = direction.normalized() * reach
	ray.collide_with_areas = true
	ray.force_raycast_update()
	if ray.is_colliding():
		var target := ray.get_collider()
		var point := ray.get_collision_point() # great for spawning a spark
		if target.has_method("take_hit"):
			target.take_hit(10)
```

Perfect for hitscan guns, lasers, line-of-sight checks and spear thrusts. Bad for a wide
sword arc: a line has no thickness, so a swing that visually clips an enemy's shoulder
will miss if the ray passes a pixel beside it. It also only returns the **first**
thing it hits — no piercing without extra work.

## ShapeCast2D: a shape, swept and checked right now

`ShapeCast2D` (new in Godot 4) is the middle ground: it sweeps a real shape along
`target_position` and, like the ray, can be forced to update on the spot. Set
`target_position` to `Vector2.ZERO` and it becomes an instant "what overlaps this shape
right now" query.

```gdscript
@onready var cast: ShapeCast2D = $ShapeCast2D

func swing() -> void:
	cast.target_position = Vector2.ZERO # instant overlap, no sweep
	cast.collide_with_areas = true
	cast.force_shapecast_update()
	for i in cast.get_collision_count():
		var target := cast.get_collider(i)
		if target and target.has_method("take_hit"):
			target.take_hit(10)
```

It has thickness like an Area2D, answers in the same frame like a RayCast2D, and returns
**multiple** hits (capped by `max_results`). The trade-off: it's a one-shot query, not a
listener — nothing tells you when something walks into a lingering hitbox later.

## The comparison

| | Area2D | RayCast2D | ShapeCast2D |
|---|---|---|---|
| Shape | any, has area | a line | any, has area |
| When results are ready | next physics frame | same frame (forced) | same frame (forced) |
| Multiple targets | yes | first hit only | yes (`max_results`) |
| Lingering hitboxes | built in (signals) | no | no — you re-query |
| Collision point | no | yes | yes, per hit |
| Fast projectiles (tunneling) | can tunnel | sweeps, won't tunnel | sweeps, won't tunnel |
| Best for | hurtboxes, AoE zones, slow attacks | hitscan, lasers, LOS | instant melee, dashes, fast bullets |

## The rule that decides it

Ask two questions:

1. **Does the hit need to land on the exact frame the button was pressed?** Short jabs,
   parries and hitscan do. Use a forced `RayCast2D` (thin) or `ShapeCast2D` (wide).
2. **Does the hitbox stay alive and keep hurting things that walk into it?** Fire, spikes,
   a spinning blade, and — importantly — every character's **hurtbox**. That's `Area2D`.

Most shipped action games end up with both: `Area2D` hurtboxes on every character, and
the *attack* side checked with whatever fits the move. What they all need on top, no
matter which node detects the overlap, is the same boring layer: teams so enemies don't
hit each other, a per-swing "already hit" list so one slash doesn't deal damage five
frames in a row, i-frames, and knockback direction.

That layer is what Saltmire Hitbox is — a drop-in Hitbox2D / Hurtbox2D pair with teams,
per-swing hit tracking, i-frames and knockback already wired, so you pick the detection
style above and skip writing the bookkeeping for the third time.
