---
title: Object pooling vs instantiate in Godot 4 — when it actually matters
description: A practical Godot 4 comparison of object pooling and plain instantiate() — what each really costs, the frame-time numbers that decide it, and a small pool you can paste into a bullet-heaven or wave-based game.
slug: godot-4-object-pooling-vs-instantiate
date: 2026-07-31
product_name: Survivors Template
product_url: https://saltmire.itch.io/survivors-template-godot
---

"Just pool everything" is the most repeated performance advice in gamedev, and it is
wrong about half the time. Pooling buys you predictable frame time, and it costs you
code you have to keep correct forever. Here is the honest comparison — what each option
really does in Godot 4, and the number that tells you which one you need.

## What `instantiate()` actually costs

Every `PackedScene.instantiate()` allocates the node tree, resolves the script, and
registers the node with the scene tree on `add_child()`. Then, when you `queue_free()`,
the node is destroyed at the end of the frame.

For a handful of nodes this is nothing. The problem is not the average — it is the
**spike**. Spawn forty enemies in one frame and that whole cost lands inside a single
`_process`, which is exactly the moment the player is already looking at a busy screen.

```gdscript
# Fine for a door, a pickup, a boss.
var bullet := BULLET.instantiate()
bullet.global_position = muzzle.global_position
add_child(bullet)
```

## What pooling actually costs

A pool trades allocation for bookkeeping: you create N objects up front, hand them out,
and take them back. Frame time gets flat and boring — which is the whole point.

```gdscript
extends Node
## Minimal pool. Pre-warms N instances, hands them out, takes them back.
const SIZE := 128

var _scene : PackedScene = preload("res://scenes/Bullet.tscn")
var _free  : Array[Node] = []

func _ready() -> void:
	for i in SIZE:
		var n := _scene.instantiate()
		n.set_process(false)
		n.set_physics_process(false)
		n.hide()
		add_child(n)
		_free.append(n)

func take() -> Node:
	# Empty pool = fall back to a real instance. Never return null: a silent
	# missing bullet is far harder to debug than one extra allocation.
	var n : Node = _free.pop_back() if not _free.is_empty() else _scene.instantiate()
	if n.get_parent() == null:
		add_child(n)
	n.show()
	n.set_process(true)
	n.set_physics_process(true)
	return n

func give_back(n: Node) -> void:
	if n == null or not is_instance_valid(n):
		return
	n.hide()
	n.set_process(false)
	n.set_physics_process(false)
	_free.append(n)
```

The catch nobody mentions: a pooled object is **never fresh**. It keeps whatever state
the last user left on it — velocity, timers, tween references, connected signals. That
is where pooling bugs come from, and they are nasty because the object works the first
time and misbehaves the fiftieth.

Give every poolable object an explicit reset and call it in `take()`:

```gdscript
func reset() -> void:
	velocity = Vector2.ZERO
	modulate = Color.WHITE
	_lifetime = 0.0
	set_deferred("monitoring", true)
```

## The comparison

| | `instantiate()` | Pool |
|---|---|---|
| Code to maintain | none | pool + a `reset()` per object |
| Frame time | spiky on bursts | flat |
| Memory | grows and shrinks | fixed, reserved up front |
| Bug class | none of its own | stale state carried between uses |
| Startup | instant | pre-warm cost at load |
| Good for | doors, pickups, bosses, UI | bullets, hordes, particles, damage numbers |

## The number that decides it

Do not guess. Open the profiler and look at **frame time**, not FPS — the average hides
exactly the spike you care about.

The rule of thumb that has held up for us: pool when you spawn and free **more than
about 20 objects per second, continuously**. Below that, `instantiate()` is not your
bottleneck and a pool is just extra surface for bugs.

A bullet-heaven is the clearest case on the "pool it" side. Hundreds of projectiles,
dozens of enemies and a damage number on every hit — all churning every single second
for a fifteen-minute run. There, allocation is not a detail; it is the frame budget.

A puzzle game spawning a tile every few seconds is the clearest case on the other side.
Pooling it would be pure cost.

## Prewarm, or your first wave stutters

If you build the pool inside `_ready()` of a scene the player is already looking at, you
moved the spike instead of removing it. Build it during the loading screen, or spread it
across frames with `await get_tree().process_frame` every N instances.

## What we do in practice

Pool the things that repeat by the hundreds: projectiles, enemies, damage numbers, hit
particles. Instantiate everything else. Two rules keep it from rotting — every poolable
object owns a `reset()`, and the pool never returns null.

If you are building a wave-based or bullet-heaven game, this pattern is not optional —
it is the difference between a run that holds 60 FPS at minute twelve and one that does
not.
