---
title: 5 Godot 4 scene transition effects (and how to build each one)
description: Fade, iris wipe, pixelate, slide, and dissolve — five working Godot 4 scene transition techniques with GDScript code you can drop in today.
slug: godot-4-scene-transitions
date: 2026-07-09
product_name: Saltmire Transitions
product_url: https://saltmire.itch.io/saltmire-transitions-scene-transition-kit-for-godot-4
---

Swapping scenes in Godot 4 is one line: `get_tree().change_scene_to_file()`. Making
that swap *feel* intentional is the part that takes effort. Here are five transition
effects — from dead simple to shader-powered — with paste-able GDScript for each.

## 1. Fade to black

The classic. A `ColorRect` at `CanvasLayer` 100 sits invisible on top of everything.
Tween its alpha to 1, change the scene, tween back to 0:

```gdscript
# SceneTransition.gd — autoload
@onready var overlay: ColorRect = $CanvasLayer/Overlay  # full-viewport, black, alpha 0

func fade_to(path: String, duration := 0.3) -> void:
    var t := create_tween()
    t.tween_property(overlay, "modulate:a", 1.0, duration)
    await t.finished
    get_tree().change_scene_to_file(path)
    t = create_tween()
    t.tween_property(overlay, "modulate:a", 0.0, duration)
```

Call it: `SceneTransition.fade_to("res://scenes/Level2.tscn")`. Squaring the tween
curve (`Tween.TRANS_SINE`) makes the fade-out feel less abrupt.

## 2. Iris wipe (circle close)

An iris wipe closes a circle over the screen, swaps the scene, then opens again.
You need one shader on the `ColorRect`:

```glsl
// iris.gdshader
shader_type canvas_item;
uniform float radius : hint_range(0.0, 1.5) = 1.5;
uniform vec2  center = vec2(0.5, 0.5);

void fragment() {
    float dist = length(UV - center);
    COLOR = vec4(0.0, 0.0, 0.0, step(radius, dist));
}
```

Then in GDScript:

```gdscript
func iris_to(path: String, duration := 0.4) -> void:
    var mat: ShaderMaterial = overlay.material
    var t := create_tween()
    t.tween_method(func(v): mat.set_shader_parameter("radius", v), 1.5, 0.0, duration)
    await t.finished
    get_tree().change_scene_to_file(path)
    t = create_tween()
    t.tween_method(func(v): mat.set_shader_parameter("radius", v), 0.0, 1.5, duration)
```

Point `center` at a character or door for a dramatic theatrical close.

## 3. Pixelate

The screen dissolves into chunky blocks before the cut. Capture the screen with
`hint_screen_texture` and floor each UV to the nearest block:

```glsl
// pixelate.gdshader
shader_type canvas_item;
uniform float block_size : hint_range(1.0, 128.0) = 1.0;
uniform sampler2D screen_texture : hint_screen_texture, filter_nearest;

void fragment() {
    vec2 vp = 1.0 / SCREEN_PIXEL_SIZE;
    vec2 snapped = floor(SCREEN_UV * vp / block_size) * block_size / vp;
    COLOR = texture(screen_texture, snapped);
}
```

Tween `block_size` from `1.0` up to `64.0` (fully pixelated), change scene, tween
back down. Looks great for retro or lo-fi aesthetics.

## 4. Slide / pan

No shader needed — just move nodes. Instantiate the next scene offscreen, then tween
both the current scene out and the new one in simultaneously:

```gdscript
func slide_to(path: String, dir := Vector2.LEFT, duration := 0.4) -> void:
    var vp := get_viewport().get_visible_rect().size
    var next := load(path).instantiate()
    next.position = -dir * vp
    get_tree().root.add_child(next)

    var t := create_tween().set_parallel()
    t.tween_property(get_tree().current_scene, "position", dir * vp, duration)
    t.tween_property(next, "position", Vector2.ZERO, duration)
    await t.finished

    get_tree().current_scene.queue_free()
    get_tree().current_scene = next
```

Pass `Vector2.RIGHT` / `Vector2.UP` / `Vector2.DOWN` to control slide direction.
Add `.set_ease(Tween.EASE_IN_OUT).set_trans(Tween.TRANS_CUBIC)` for a polished
mobile-menu feel.

## 5. Dissolve (noise dither)

A dissolve removes pixels in a pseudo-random order using a grayscale noise texture
as a threshold map — much more interesting than a uniform fade:

```glsl
// dissolve.gdshader
shader_type canvas_item;
uniform float threshold : hint_range(0.0, 1.0) = 0.0;
uniform sampler2D noise : hint_default_white;
uniform sampler2D screen_texture : hint_screen_texture, filter_nearest;

void fragment() {
    float n = texture(noise, UV).r;
    if (n < threshold) { discard; }
    COLOR = texture(screen_texture, SCREEN_UV);
}
```

Assign any seamless noise texture to `noise`, then tween `threshold` from `0.0` to
`1.0` to dissolve out. Use a SubViewport to capture the outgoing scene so the
dissolve continues to run after the scene has already changed.

## Which one to use

| Effect | Complexity | Best for |
|--------|-----------|----------|
| Fade | Trivial | Any genre — never wrong |
| Iris | One shader | Dramatic story beats, cutscenes |
| Pixelate | One shader | Retro, lo-fi, pixel-art games |
| Slide | Pure GDScript | Menu flows, mobile feel |
| Dissolve | Shader + noise texture | Cinematic, horror, RPG |

## Skip the wiring

Each effect above is ~15 lines of code. The time cost is the autoload setup,
managing which `CanvasLayer` owns what, and making the `await`-able API safe against
overlapping calls. If you want all five (plus wipes and a smooth fade-in-on-load
default) as a single drop-in for Godot 4, that is what Saltmire Transitions is.
