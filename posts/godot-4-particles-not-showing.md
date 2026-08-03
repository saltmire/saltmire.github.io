---
title: "Godot 4 GPUParticles2D not showing? 5 reasons your particles aren't appearing"
description: Your Godot 4 GPUParticles2D is in the scene but nothing shows up. Here are the 5 real causes — missing process material, culled visibility rect, one_shot traps, lifetime too short, and emitting left false — each with the exact fix.
slug: godot-4-particles-not-showing
date: 2026-08-02
product_name: Saltmire Spark
product_url: https://saltmire.itch.io/saltmire-spark
---

You added a `GPUParticles2D`, pressed Play, and the node is there in the tree — but
zero particles appear. No error. Just silence. This is one of Godot 4's quietest
failure modes because the engine never warns you when a particle system can't show
anything. Work through these five causes in order; one of them is almost certainly it.

## 1. No process material assigned

**Symptom.** Node is in the tree, the inspector shows `Process Material: [empty]`, no
particles appear even though `emitting = true`.

**Cause.** `GPUParticles2D` without a `ParticleProcessMaterial` emits nothing and
gives no error. It's easy to forget when you duplicate an existing node, detach the
resource, or instantiate the node in code.

**Fix.** Always assign a material, even a default one:

```gdscript
var particles := GPUParticles2D.new()
var mat := ParticleProcessMaterial.new()
mat.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_POINT
mat.initial_velocity_min = 50.0
mat.initial_velocity_max = 100.0
particles.process_material = mat
add_child(particles)
```

If you're doing it in the editor, select the node, click the `Process Material`
property in the Inspector, and pick **New ParticleProcessMaterial**.

## 2. `emitting` is false

**Symptom.** Particles existed in a previous scene, you reset or duplicated the node,
and now nothing comes out.

**Cause.** `emitting` defaults to `true` in a fresh node, but gets serialized on save.
Resetting the scene, calling `queue_free()` and re-instantiating, or setting it false
in an animation player and never restoring it will silence the emitter with no
feedback.

**Fix.** If you're spawning a burst in code, make sure you set `emitting = true` after
any other property setup:

```gdscript
func burst(pos: Vector2) -> void:
    var p: GPUParticles2D = BURST_SCENE.instantiate()
    p.position = pos
    p.emitting = true   # must be explicit — don't rely on the saved default
    add_child(p)
```

And after a `one_shot` burst completes, `emitting` is automatically set back to
`false` by the engine — this is correct behavior, not a bug. To replay the effect,
call `restart()`:

```gdscript
particles.one_shot = true
particles.restart()   # resets the timer and starts emitting again
```

## 3. Visibility rect too small (particles culled)

**Symptom.** Particles appear in the editor's 2D viewport but disappear at runtime,
or only show near the center of the screen.

**Cause.** Godot 4 frustum-culls `GPUParticles2D` using the node's
`visibility_rect`. The default is a tiny `Rect2(-100, -100, 200, 200)`. If particles
travel outside that rect — especially for large explosions, projectile trails, or
slow heavy particles — they vanish the moment the computed position leaves the box.

**Fix.** Fit the rect to your actual spread. You can ask Godot to estimate it for you:
in the editor, select the node while it's emitting and press the **Visibility Rect**
button in the toolbar to auto-calculate. In code, size it conservatively:

```gdscript
# a symmetric 512×512 box centred on the emitter — adjust to fit your spread:
particles.visibility_rect = Rect2(-256, -256, 512, 512)
```

For very dynamic effects that change size at runtime, set it once to the maximum
possible extent and leave it; the cost of a slightly oversized rect is negligible.

## 4. `lifetime` or `amount` are too small to see

**Symptom.** A particle or two flickers for a frame and disappears.

**Cause.** The engine allocates exactly `amount` particles and recycles them as they
die. If `lifetime` is `0.1` and `amount` is `4`, you get four particles that live for
a tenth of a second and that's it. At 60 fps they're visible for ~6 frames — fast
enough to read as a flicker or not register at all.

**Fix.** For a hit burst you actually want to see: `amount` of at least 8–12, and
`lifetime` of 0.4–0.8 seconds. If it still looks sparse, also check `amount_ratio` —
it scales the actual emission count between 0 and 1 and defaults to 1.0, but can be
set to 0 by an animation.

```gdscript
particles.amount = 12
particles.lifetime = 0.5
particles.amount_ratio = 1.0  # full count; check this if amount looks right but few spawn
```

## 5. The `one_shot` trap — particles fire once at scene load and stop

**Symptom.** The burst works exactly once (at startup), then never again.

**Cause.** `one_shot = true` + `emitting = true` on scene load means the system fires
immediately and marks itself done. The next time your code calls `emitting = true` on
an already-exhausted one-shot system, nothing happens.

**Fix.** Start `one_shot` emitters with `emitting = false` and use `restart()` to fire
them on demand. This guarantees a clean run each time:

```gdscript
@onready var particles := $HitParticles  # one_shot = true in the inspector

func play_hit() -> void:
    particles.restart()   # safe to call even if already running — resets and re-emits
```

`restart()` is the canonical way to trigger a `one_shot` effect from code; it also
resets the randomization seed, so each burst looks fresh.

## What all five have in common

Every one of these is a silent no-op: the node exists, no error is thrown, and you
get nothing. The engine provides no warning when a particle system can't render, which
is what makes these bugs hard to notice. If you want guaranteed visible bursts without
wiring `GPUParticles2D` from scratch — process material, lifetime, amount, visibility
rect and all — that's exactly what Saltmire Spark does with a single call.
