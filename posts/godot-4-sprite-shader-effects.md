---
title: 5 Godot 4 sprite shader effects you can build in one script
description: Dissolve, outline, hit-flash, freeze, and hologram — five Godot 4 canvas_item shader effects with copy-paste GDScript and .gdshader code for each.
slug: godot-4-sprite-shader-effects
date: 2026-08-16
product_name: Saltmire FX
product_url: https://saltmire.itch.io/saltmire-fx
---

A `Sprite2D` with a flat texture reads as static. A `Sprite2D` that can dissolve,
outline, flash, freeze, or glow reads as *alive*. All five of those are small
`canvas_item` shaders — no particles, no extra nodes, just a `ShaderMaterial` and a
uniform you drive from a `Tween`. Here are five you can paste in today.

## 1. Dissolve

A noise texture decides, pixel by pixel, which parts of the sprite disappear first.
Tween `threshold` from 0 to 1 and the sprite erodes away instead of just fading:

```glsl
// dissolve.gdshader
shader_type canvas_item;
uniform float threshold : hint_range(0.0, 1.0) = 0.0;
uniform sampler2D noise : hint_default_white;

void fragment() {
    vec4 c = texture(TEXTURE, UV);
    float n = texture(noise, UV).r;
    if (n < threshold) { discard; }
    COLOR = c;
}
```

```gdscript
func dissolve(sprite: CanvasItem, duration := 0.6) -> void:
    var mat: ShaderMaterial = sprite.material
    create_tween().tween_method(
        func(v): mat.set_shader_parameter("threshold", v), 0.0, 1.0, duration)
```

Any seamless grayscale noise texture works for `noise` — a cheap Perlin or Worley
texture gives you a very different silhouette than plain static.

## 2. Outline

Sample the alpha channel a few pixels in each direction; if the center pixel is
transparent but a neighbor isn't, that pixel is edge:

```glsl
// outline.gdshader
shader_type canvas_item;
uniform vec4 outline_color : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float width : hint_range(0.0, 4.0) = 1.0;

void fragment() {
    vec4 c = texture(TEXTURE, UV);
    vec2 px = width / vec2(textureSize(TEXTURE, 0));
    float a = texture(TEXTURE, UV + vec2(px.x, 0)).a
            + texture(TEXTURE, UV - vec2(px.x, 0)).a
            + texture(TEXTURE, UV + vec2(0, px.y)).a
            + texture(TEXTURE, UV - vec2(0, px.y)).a;
    if (c.a < 0.1 && a > 0.0) {
        COLOR = outline_color;
    } else {
        COLOR = c;
    }
}
```

Toggle it from GDScript for a "targetable" or "selected" state:

```gdscript
func set_outlined(sprite: CanvasItem, on: bool) -> void:
    (sprite.material as ShaderMaterial).set_shader_parameter("width", 1.0 if on else 0.0)
```

Works on any sprite with transparent padding — no separate outline sprite to keep in
sync.

## 3. Hit-flash

The fastest way to sell a hit: slam the sprite to solid white for a frame, then let
it fade back. One uniform, one mix:

```glsl
// flash.gdshader
shader_type canvas_item;
uniform float amount : hint_range(0.0, 1.0) = 0.0;

void fragment() {
    vec4 c = texture(TEXTURE, UV);
    COLOR = vec4(mix(c.rgb, vec3(1.0), amount), c.a);
}
```

```gdscript
func flash(sprite: CanvasItem, duration := 0.12) -> void:
    var mat: ShaderMaterial = sprite.material
    mat.set_shader_parameter("amount", 1.0)
    create_tween().tween_method(
        func(v): mat.set_shader_parameter("amount", v), 1.0, 0.0, duration)
```

Fire this on every `take_damage()` call and hits instantly feel like they landed,
even before a damage number or knockback shows up.

## 4. Freeze (grayscale + tint)

Desaturate the sprite and push it toward a cold blue — reads as "frozen" or
"stunned" without swapping a single texture:

```glsl
// freeze.gdshader
shader_type canvas_item;
uniform float amount : hint_range(0.0, 1.0) = 0.0;
uniform vec4 tint : source_color = vec4(0.6, 0.8, 1.0, 1.0);

void fragment() {
    vec4 c = texture(TEXTURE, UV);
    float gray = dot(c.rgb, vec3(0.299, 0.587, 0.114));
    vec3 frozen = mix(vec3(gray), tint.rgb, 0.5);
    COLOR = vec4(mix(c.rgb, frozen, amount), c.a);
}
```

```gdscript
func set_frozen(sprite: CanvasItem, frozen: bool, duration := 0.2) -> void:
    var mat: ShaderMaterial = sprite.material
    create_tween().tween_method(
        func(v): mat.set_shader_parameter("amount", v),
        mat.get_shader_parameter("amount"), 1.0 if frozen else 0.0, duration)
```

Pair it with `Engine.time_scale` on that one enemy (via a per-node "local slow"
trick, since `time_scale` is global) and the freeze reads as more than cosmetic.

## 5. Hologram

Horizontal scanlines plus a fresnel-style rim glow, both driven by `TIME`, turns a
flat sprite into a sci-fi projection:

```glsl
// hologram.gdshader
shader_type canvas_item;
uniform vec4 glow_color : source_color = vec4(0.3, 0.9, 1.0, 1.0);
uniform float scan_speed : hint_range(0.0, 10.0) = 3.0;

void fragment() {
    vec4 c = texture(TEXTURE, UV);
    float scan = sin((UV.y * 40.0) - TIME * scan_speed) * 0.5 + 0.5;
    float rim = pow(1.0 - abs(UV.x - 0.5) * 2.0, 3.0);
    vec3 col = mix(c.rgb, glow_color.rgb, 0.4 + rim * 0.3);
    COLOR = vec4(col, c.a * (0.7 + scan * 0.3));
}
```

No GDScript needed to drive this one — `TIME` animates it for free once the
material is assigned. Just set `glow_color` per-sprite if you want factions or
rarities to glow differently.

## Wiring five shaders without five headaches

Individually each of these is one small `.gdshader` file and a couple of uniforms.
The part that actually eats time is the plumbing: giving every sprite its own
`ShaderMaterial` instance (share one and every dissolve syncs together, which is
almost never what you want), keeping `amount`/`threshold` tweens from fighting
each other when two effects fire on the same frame, and remembering which uniform
name goes with which shader across a whole project. That bookkeeping is exactly
what Saltmire FX collapses into a one-line call per effect.
