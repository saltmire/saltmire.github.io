---
title: How to add motion trails and afterimages in Godot 4
description: A step-by-step Godot 4 tutorial for motion trails and dash afterimages — a sprite-snapshot scene, a configurable trail emitter, and tips for making them look great during fast movement.
slug: godot-4-motion-trail-afterimage
date: 2026-08-13
product_name: Saltmire Trail
product_url: https://saltmire.itch.io/saltmire-trail
---

Motion trails — those fading ghost copies left behind a dashing character — are one
of the quickest wins for game feel. They make speed *readable* without any physics
changes. Here's how to build one from scratch in Godot 4, then tips for turning it
into a reusable component.

## How it works

The idea is simple: every N milliseconds, take a snapshot of the character's current
sprite frame and position, then fade that snapshot out. Stack several snapshots and
you get a trail. No physics, no shaders required to start.

## Step 1: the ghost scene

Create a new scene with a `Sprite2D` root. Name it `TrailGhost`. Give it this script:

```gdscript
class_name TrailGhost extends Sprite2D

func play(tex: Texture2D, region: Rect2, use_region: bool,
          at: Vector2, flipped_h: bool, alpha_start := 0.7,
          duration := 0.25) -> void:
    texture = tex
    region_rect = region
    region_enabled = use_region
    global_position = at
    flip_h = flipped_h
    modulate.a = alpha_start
    var t := create_tween()
    t.tween_property(self, "modulate:a", 0.0, duration) \
        .set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
    t.tween_callback(queue_free)
```

This ghost reads the source sprite's current frame data, drops itself at the right
world position, and auto-destroys after fading. The `region_rect` copy is what makes
the snapshot land on the correct animation frame rather than the whole spritesheet.

## Step 2: the trail emitter

In your character scene, add a child `Node2D` called `Trail`. Give it this script,
and export a reference to the character's `AnimatedSprite2D` (or `Sprite2D`):

```gdscript
extends Node2D

@export var ghost_scene: PackedScene
@export var source: AnimatedSprite2D
@export var interval := 0.04          # seconds between ghosts
@export var ghost_duration := 0.25
@export var alpha_start := 0.65

var _timer := 0.0
var _active := false

func activate() -> void:  _active = true
func deactivate() -> void: _active = false

func _process(delta: float) -> void:
    if not _active:
        return
    _timer += delta
    if _timer < interval:
        return
    _timer = 0.0
    _spawn_ghost()

func _spawn_ghost() -> void:
    if not source or not ghost_scene:
        return
    var g: TrailGhost = ghost_scene.instantiate()
    get_tree().current_scene.add_child(g)   # world-space, not parented to character
    var frames := source.sprite_frames
    var anim := source.animation
    var frame_idx := source.frame
    var tex := frames.get_frame_texture(anim, frame_idx)
    g.play(tex, Rect2(), false,
           source.global_position, source.flip_h,
           alpha_start, ghost_duration)
```

Adding the ghost to the *scene root* instead of the character means it stays at the
right world position even when the character moves. If you parent it to the character,
it follows along and the trail collapses.

## Step 3: wire it to a dash

Call `activate()` and `deactivate()` around any movement where you want a trail.
A typical dash looks like this in the character script:

```gdscript
func _dash() -> void:
    $Trail.activate()
    var t := create_tween()
    t.tween_property(self, "velocity", dash_dir * dash_speed, 0.0)
    await get_tree().create_timer(dash_duration).timeout
    $Trail.deactivate()
```

For continuous speed-based trails (racing games, bullet hell), you can skip the
manual toggle and drive it from speed instead:

```gdscript
func _process(delta: float) -> void:
    var spd := velocity.length()
    if spd > trail_threshold:
        $Trail.activate()
    else:
        $Trail.deactivate()
```

## Step 4: make it look good

A few small tweaks make a big difference:

**Interval vs duration ratio** — if `interval` is close to `ghost_duration`, ghosts
are sparse and the trail feels dotted. For a solid streak, keep `interval` at roughly
one-sixth of `ghost_duration` (e.g. 0.04s / 0.25s).

**Tint the ghosts** — multiply `modulate` by a color before calling `play()`. Cyan
works well for ice dashes; orange for fire. Set it on the `Trail` node as an export:

```gdscript
@export var tint := Color.WHITE

# inside _spawn_ghost(), after g.play():
g.modulate *= tint
```

**Z-index** — give `TrailGhost` a lower `z_index` than the character (e.g. -1) so
the trail sits *behind* the sprite, not on top of it.

**Layer trails on AnimatedSprite2D frames** — if your character uses a packed
spritesheet with `region_enabled = true`, read `texture_region_rect` instead of
`region_rect` and set `region_enabled = true` on the ghost. The script above leaves
a `Rect2()` placeholder — swap it for `source.get_rect()` if your frames are
packed that way.

## When to pool

`queue_free` is fine for short dashes where you spawn 5–10 ghosts per dash. Once
you're emitting dozens per second — flying enemies, bullet patterns — the alloc
pressure adds up. A small pool (pre-spawn 20 ghosts, hide/show rather than
instantiate/free) keeps the frame time flat. The same pooling pattern from the
damage-numbers post applies directly here.

## The finished trail

That's the core: a self-destructing ghost scene, a timer-driven emitter, and an
on/off signal tied to your movement logic. Tweak interval, duration, and tint per
ability and you get a different personality for every dash in the game. If you'd
rather drop in a single addon with pooling, color modes, and a one-call API already
wired up, that's exactly what Saltmire Trail handles.
