---
title: 6 Godot 4 game feel tricks (each just a few lines of GDScript)
description: Squash-and-stretch, sprite flash, damage numbers, knockback, slow-motion and a camera punch — six drop-in Godot 4 game feel techniques with copy-paste GDScript.
slug: godot-4-game-feel-tricks
date: 2026-07-18
product_name: Saltmire Impact
product_url: https://saltmire.itch.io/saltmire-impact
---

"Game feel" is the difference between a hit that just subtracts HP and a hit that
*lands*. In Godot 4 almost none of it needs plugins — it's small, cheap touches
stacked on top of each other. Here are six you can paste in today, each only a few
lines.

## 1. Squash and stretch on impact

Nothing sells a hit like a quick scale pop. Punch the scale up, then let it spring
back with an elastic transition:

```gdscript
func pop(node: Node2D, amount := 0.25, duration := 0.25) -> void:
    var base := node.scale
    var t := create_tween()
    node.scale = base * (1.0 + amount)
    t.tween_property(node, "scale", base, duration) \
        .set_trans(Tween.TRANS_ELASTIC).set_ease(Tween.EASE_OUT)
```

Call `pop($Sprite2D)` on landing, on pickup, on button press — anywhere you want a
tiny "yes".

## 2. Sprite flash on hit

A single white frame reads instantly as "that connected". Drive a `flash_amount`
uniform on a tiny shader and tween it back to zero:

```glsl
// flash.gdshader
shader_type canvas_item;
uniform float flash_amount : hint_range(0.0, 1.0) = 0.0;
void fragment() {
    vec4 c = texture(TEXTURE, UV);
    COLOR = vec4(mix(c.rgb, vec3(1.0), flash_amount), c.a);
}
```

```gdscript
func flash(sprite: CanvasItem, duration := 0.12) -> void:
    var mat: ShaderMaterial = sprite.material
    mat.set_shader_parameter("flash_amount", 1.0)
    create_tween().tween_method(
        func(v): mat.set_shader_parameter("flash_amount", v), 1.0, 0.0, duration)
```

## 3. Pooled damage numbers

Floating numbers give weight to every hit — but instancing a Label per hit thrashes
the GC. Spawn from a small pool instead and tween position + fade:

```gdscript
func damage_number(pos: Vector2, value: int) -> void:
    var label := _pool_get()          # reuse a Label from a preallocated array
    label.text = str(value)
    label.global_position = pos
    label.modulate.a = 1.0
    var t := create_tween().set_parallel()
    t.tween_property(label, "global_position", pos + Vector2(0, -32), 0.5)
    t.tween_property(label, "modulate:a", 0.0, 0.5)
    t.chain().tween_callback(func(): _pool_return(label))
```

The pool is just an array you fill on `_ready()` and hand out round-robin — no
`instantiate()` on the hot path.

## 4. Knockback that eases out

Instant teleport-back feels cheap; a short eased slide feels physical:

```gdscript
func knockback(body: Node2D, dir: Vector2, strength := 180.0, duration := 0.15) -> void:
    var target := body.global_position + dir.normalized() * strength
    create_tween().tween_property(body, "global_position", target, duration) \
        .set_trans(Tween.TRANS_QUART).set_ease(Tween.EASE_OUT)
```

For a `CharacterBody2D` you'd feed this into `velocity` instead, but the easing idea
is the same: fast start, soft stop.

## 5. Slow-motion on the big hit

Reserve time dilation for moments that earn it — a finisher, a boss stagger. Drop
`Engine.time_scale`, wait in *real* time (unscaled), then ramp back:

```gdscript
func slowmo(scale := 0.05, real_seconds := 0.15) -> void:
    Engine.time_scale = scale
    var timer := get_tree().create_timer(real_seconds, true, false, true) # ignore_time_scale
    await timer.timeout
    create_tween().tween_method(
        func(v): Engine.time_scale = v, scale, 1.0, 0.2)
```

The `true` at the end of `create_timer` is what makes it ignore `time_scale` — miss
that and your slow-mo waits in slow-mo and never ends.

## 6. Camera punch

A quick directional shove on the camera, snapping back, adds impact without a full
shake routine:

```gdscript
func punch(cam: Camera2D, dir: Vector2, amount := 8.0, duration := 0.12) -> void:
    var base := cam.offset
    cam.offset = base + dir.normalized() * amount
    create_tween().tween_property(cam, "offset", base, duration) \
        .set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
```

Point `dir` opposite the hit — punch the camera *away* from the impact and the brain
fills in the force.

## Stacking them

The magic is in combining: on a real hit you might `flash()` the target, `pop()` it,
spawn a `damage_number()`, `knockback()` it, and `punch()` the camera — all in the
same frame. Individually each is a nudge; together they're the difference between
flat and juicy. The only hard part is wiring them into one clean call and keeping the
tweens from stepping on each other, which is exactly the boilerplate Saltmire Impact
folds into a single line.
