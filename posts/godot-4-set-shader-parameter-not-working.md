---
title: "Fixing set_shader_parameter not working in Godot 4"
description: Godot 4 shader uniform won't change from code, or a hit flash lights up every enemy at once? The 5 real causes of set_shader_parameter doing nothing — the Godot 3 rename, shared materials, silent typos, wrong tween paths, use_parent_material — and the exact fix for each.
slug: godot-4-set-shader-parameter-not-working
date: 2026-10-15
product_name: Saltmire FX
product_url: https://saltmire.itch.io/saltmire-fx
---

Sprite shaders are the one place in Godot 4 where wrong code doesn't crash — it just
quietly does nothing. You call a setter, the sprite doesn't change, and there is no error
to search for. Or worse: it works, and lights up all twelve enemies on screen.

The symptoms that bring people here:

- `Invalid call. Nonexistent function 'set_shader_param' in base 'ShaderMaterial'.`
- The uniform changes fine in the inspector, but nothing happens from code.
- One enemy gets hit and **every** enemy flashes white.
- `Invalid property path 'shader_param/progress'` from a tween.

Five causes, ordered by how often they show up.

## 1. You're calling the Godot 3 name

**Symptom.** `Nonexistent function 'set_shader_param'`, or an old tutorial's
`material.set("shader_param/flash", 1.0)` that fails silently.

**Cause.** Godot 4 renamed it. `shader_param` is gone; it's `shader_parameter` everywhere —
the method, the property path, the `get_` version.

**Fix.**

```gdscript
# Godot 3 — dead
material.set_shader_param("flash_amount", 1.0)
material.set("shader_param/flash_amount", 1.0)

# Godot 4
material.set_shader_parameter("flash_amount", 1.0)
```

Note which half fails. The method call raises an error you can see. The
`material.set("shader_param/...")` form is a generic property write — it returns nothing
and warns nothing, which is why it survives in copy-pasted code for months.

## 2. The material is shared between every instance

**Symptom.** The shader works, but hitting one enemy flashes the whole screen's worth
of them.

**Cause.** A `ShaderMaterial` saved as a `.tres` file, or assigned once in a scene, is
**one resource**. Every instance of that scene points at the same object. Setting a
parameter sets it for all of them. This is also why it looks right in a single-enemy
test scene and breaks the moment you spawn a crowd.

**Fix.** Give each instance its own copy on spawn:

```gdscript
func _ready() -> void:
    # shallow duplicate: own parameter values, same compiled Shader
    var mat := sprite.material as ShaderMaterial
    if mat:
        sprite.material = mat.duplicate()
```

Or do it without code: select the material in the inspector and tick **Resource >
Local to Scene**. Each instantiated scene then gets its own copy automatically.

Worth knowing: the per-instance uniform shortcut
(`set_instance_shader_parameter`) lives on `GeometryInstance3D`, not on `CanvasItem`. In
2D, `duplicate()` or Local to Scene is the answer.

## 3. The uniform name doesn't match — and Godot won't tell you

**Symptom.** No error at all. The call runs, nothing changes.

**Cause.** `set_shader_parameter()` accepts any name. If no uniform matches — a typo, a
renamed uniform, the wrong shader on the node — the value is stored and never read.
There is no warning.

**Fix.** Check against the shader's actual uniform list instead of guessing:

```gdscript
func _ready() -> void:
    var mat := sprite.material as ShaderMaterial
    for u in mat.shader.get_shader_uniform_list():
        print(u["name"], " : ", u["type"])
```

Two related traps:

- A uniform you never declared in the shader won't appear in the inspector either — that's
  your fastest check. Visible in the inspector, ignored from code means a typo in the
  string, not a shader problem.
- `get_shader_parameter()` returns `null` when nothing has been set on that material. It
  does not fall back to the default written in the shader, so don't use it to read a
  starting value.

## 4. A tween is animating the wrong property path

**Symptom.** `Invalid property path`, or a tween that completes instantly with no visible
change.

**Cause.** Tweening a uniform means tweening a property **on the material**, with the
Godot 4 path, not the node and not the Godot 3 prefix.

**Fix.**

```gdscript
func flash() -> void:
    var mat := sprite.material as ShaderMaterial
    mat.set_shader_parameter("flash_amount", 1.0)
    var tw := create_tween()
    tw.tween_property(mat, "shader_parameter/flash_amount", 0.0, 0.15)
```

`create_tween()` on the node binds the tween's life to that node, so a dying enemy can't
leave a tween poking at a freed material.

## 5. `use_parent_material` is on

**Symptom.** Setting the parameter on the node's own material does nothing, and the
inspector seems to ignore the material too.

**Cause.** `CanvasItem.use_parent_material` is checked (sometimes inherited from a scene
you copied). The node renders with the parent's material; its own is unused.

**Fix.** Uncheck it, or set the parameter on whichever material actually renders:

```gdscript
var mat := sprite.material as ShaderMaterial
if sprite.use_parent_material:
    mat = sprite.get_parent().material as ShaderMaterial
```

## The quick triage order

When a uniform won't move, go in this order: is the name in
`get_shader_uniform_list()`? Is `use_parent_material` off? Is the material a
`duplicate()` or Local to Scene? Is the tween path
`shader_parameter/<name>`? Four checks and the silent cases stop being mysterious.

Most of this is plumbing, not effects work — which is the thinking behind Saltmire FX.
Each call (`FX.hit_flash($Sprite2D)`, `FX.dissolve($Sprite2D)`, outline, freeze,
hologram) builds a fresh `ShaderMaterial` on the node you passed in, so causes 1, 2 and 3
can't reach your code: nothing is shared between instances and no uniform name is spelled
on your side. The tweens come from `target.create_tween()`, for the lifetime reason in
cause 4. It's MIT and the shaders are plain `.gdshader` files, so you can read exactly
what it does, or lift the pattern and keep writing it yourself — the five checks above are
the whole of it either way.
