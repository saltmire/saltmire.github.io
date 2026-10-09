---
title: What I learned making a smooth 2D camera follow in Godot 4
description: Lessons from building a Camera2D that follows the player in Godot 4 — smoothing that doesn't jitter, limits from the tilemap, teleports without a swoosh, and look-ahead that doesn't fight screen shake.
slug: godot-4-camera2d-follow-smoothing-limits
date: 2026-10-09
product_name: Saltmire Impact
product_url: https://saltmire.itch.io/saltmire-impact
---

A 2D camera looks like a five-minute job. Drop a `Camera2D` under the player, tick a box,
done. Then the sprite starts to shimmer, the camera shows the grey void past the edge of
the level, and every respawn swooshes across the whole map. Here is what I learned making
the camera feel right, in the order the problems showed up.

## Lesson 1: a child camera is fine — until it isn't

The fastest setup is a `Camera2D` as a child of the player. It follows perfectly because
it *is* the player's transform. That's also the problem: when the player is freed on
death, the camera goes with it and the view snaps to the origin for a frame.

What I use now is a camera that lives in the level and chases a target:

```gdscript
extends Camera2D

@export var target: Node2D

func _physics_process(_delta: float) -> void:
	if is_instance_valid(target):
		global_position = target.global_position
```

The camera survives the player, can be pointed at a boss or a cutscene marker, and the
`is_instance_valid` check means a freed target just leaves the camera where it was.

## Lesson 2: smoothing jitter is a timing problem, not a speed problem

I turned on `position_smoothing_enabled`, and the player sprite started to vibrate while
running. I spent too long tweaking `position_smoothing_speed`. No value fixed it.

The cause: the player moves in `_physics_process` (60 Hz by default) and the camera was
updating at the render rate. On a 144 Hz monitor they disagree on most frames, and
smoothing makes the mismatch visible. Make both run on the same clock:

```gdscript
func _ready() -> void:
	process_callback = Camera2D.CAMERA2D_PROCESS_PHYSICS
	position_smoothing_enabled = true
	position_smoothing_speed = 6.0
```

That fixed 90% of it. On Godot 4.3+, turning on **Project Settings → Physics → Common →
Physics Interpolation** fixed the rest, because it renders the in-between positions
for both the player and the camera. If you use pixel art, also check
`rendering/2d/snap/snap_2d_transforms_to_pixel` — sub-pixel camera positions make
pixel sprites shimmer even when the timing is right.

## Lesson 3: read the limits from the level instead of typing them in

I hand-typed `limit_right = 3200` for the first level. The second level was a different
size, and I forgot. The tilemap already knows how big the level is:

```gdscript
func fit_to_tilemap(layer: TileMapLayer) -> void:
	var used := layer.get_used_rect()
	var cell := layer.tile_set.tile_size
	var top_left := layer.to_global(Vector2(used.position * cell))
	var bottom_right := layer.to_global(Vector2(used.end * cell))
	limit_left = int(top_left.x)
	limit_top = int(top_left.y)
	limit_right = int(bottom_right.x)
	limit_bottom = int(bottom_right.y)
```

Two details I got wrong first. Limits are in **global** coordinates, so a tilemap that
isn't at the origin needs the `to_global` call. And if the level is smaller than the
screen, Godot can't satisfy both limits at once, so one side wins and the level sits
off-centre. For small rooms, I skip the limits and centre the camera on the room.

Turn on `limit_smoothed = true` too. Without it, the camera slides smoothly everywhere
except at the edge, where it suddenly stops dead.

## Lesson 4: teleports need `reset_smoothing()`

With smoothing on, every respawn, door and checkpoint made the camera glide across the
whole level to catch up. It looks like a bug because it is one. After moving the target
instantly, tell the camera to jump too:

```gdscript
func snap_to_target() -> void:
	global_position = target.global_position
	reset_smoothing()
```

I call this from the respawn and from scene load. Calling it from `_ready()` alone
wasn't enough, because the target sometimes got its spawn position a frame later, so
I added a `call_deferred("snap_to_target")` there.

## Lesson 5: look-ahead and screen shake both want `offset`

Platformers and top-down shooters feel better when the camera leans in the direction
you're moving, so you can see what's coming. The clean way is `offset`, because it
doesn't fight the smoothing on `position`:

```gdscript
@export var look_ahead := 48.0
@export var look_speed := 4.0

func _physics_process(delta: float) -> void:
	if not is_instance_valid(target):
		return
	global_position = target.global_position
	var dir := Vector2.ZERO
	var vel = target.get("velocity")  # null if the target has no velocity
	if vel is Vector2:
		dir = vel.normalized()
	offset = offset.lerp(dir * look_ahead, look_speed * delta)
```

Then I added screen shake, which *also* writes to `offset`. The two overwrote each
other every frame. Shake vanished while running, and stopping mid-shake left the camera
crooked. The fix is to keep each effect in its own variable and add them together in one
place:

```gdscript
var _look := Vector2.ZERO
var _shake := Vector2.ZERO

func _physics_process(delta: float) -> void:
	# ...update _look as above, update _shake from your shake code...
	offset = _look + _shake
```

That one line keeps both effects working.

## What I'd do differently starting over

Start with a free-standing camera that follows a target, set to the physics clock. Read
limits from the level, and write `snap_to_target()` before the first respawn exists.
Treat `offset` as shared: anything that moves the view adds its own term instead of
writing directly.

That last point is where most of my camera bugs came from. Shake, hit-stop and
look-ahead all touch the same few properties at the same moment, and mixing them by
hand gets fiddly fast. That combination is what I eventually packaged up, so I stopped
rewriting it every project.
