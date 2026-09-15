---
title: "Godot 4 camera shake not working right? 4 causes and fixes"
description: Your Godot 4 camera shake barely moves, snaps back instantly, or drifts permanently off-center. Here are the 4 real causes — shaking position instead of offset, overlapping shakes fighting each other, offset never getting reset, and frame-rate-dependent decay — each with the exact fix.
slug: godot-4-camera-shake-not-working
date: 2026-09-07
product_name: Saltmire Impact
product_url: https://saltmire.itch.io/saltmire-impact
---

You wire up a quick camera shake for hits, and something's off. Either it barely
registers, it snaps back the instant it starts, or — worst case — the camera stays
crooked long after the shake should have stopped. None of these are random. Here are
the four causes, ordered by how often they show up.

## 1. The shake writes to `position` instead of `offset`

**Symptom.** The shake fires — you can see the value change in the debugger — but
on screen the camera doesn't move, or barely twitches.

**Cause.** Most camera-follow code sets `Camera2D.position` (or
`global_position`) every frame to track the player: `position = target.global_position`.
If your shake also writes to `position`, whichever one runs last that frame wins.
Since follow logic usually runs every `_process()` tick right alongside your shake,
the follow call quietly overwrites the shake before the frame ever renders.

**Fix.** Never shake `position` — shake `offset`. It's a separate property Camera2D
gives you specifically so shake and follow don't collide:

```gdscript
# follow logic — untouched, keeps writing to position every frame
func _process(_delta: float) -> void:
    global_position = target.global_position

# shake — writes to offset instead, so it never fights the line above
func shake(amount: float, duration: float) -> void:
    var t := create_tween()
    var elapsed := 0.0
    while elapsed < duration:
        offset = Vector2(randf_range(-amount, amount), randf_range(-amount, amount))
        await get_tree().create_timer(0.02).timeout
        elapsed += 0.02
    offset = Vector2.ZERO
```

## 2. Overlapping shakes fight each other

**Symptom.** Rapid hits (a combo, a burst of bullets) make the camera snap and
stutter instead of shaking smoothly — it looks broken exactly when it should look
most intense.

**Cause.** Each `shake()` call above starts its own loop or tween writing to the
same `offset`. Trigger a second shake before the first finishes and now two timers
are both setting `offset` every frame — whichever one updates last on a given frame
wins, so the camera jumps between two unrelated random values instead of blending.

**Fix.** Track the strongest active shake instead of letting every call run its own
independent loop, and only ever start one shake process:

```gdscript
var _shake_strength := 0.0
var _shake_decay := 4.0  # per second

func add_shake(amount: float) -> void:
    _shake_strength = max(_shake_strength, amount)  # take the strongest hit, don't stack

func _process(delta: float) -> void:
    if _shake_strength > 0.01:
        offset = Vector2(randf_range(-1, 1), randf_range(-1, 1)) * _shake_strength
        _shake_strength = lerp(_shake_strength, 0.0, _shake_decay * delta)
    else:
        offset = Vector2.ZERO
```

Now three hits in a row just raise `_shake_strength` back up — one continuous decay
curve, no fighting timers.

## 3. `offset` never gets reset when the shake ends

**Symptom.** After the last hit of a fight, the camera stays permanently nudged
off-center — sometimes only noticeable because the player feels slightly
off-screen.

**Cause.** A `Tween` that shakes `offset` and gets interrupted (the node dies, the
scene changes, a `queue_free()` fires mid-tween) never reaches its own cleanup step,
so whatever random value it last wrote stays there forever.

**Fix.** Don't rely on the tween finishing naturally — reset explicitly in
`_exit_tree()`, and prefer the decay-based approach in cause #2, which always
converges back to `Vector2.ZERO` on its own instead of depending on a tween
completing:

```gdscript
func _exit_tree() -> void:
    offset = Vector2.ZERO
```

## 4. Shake decays at a fixed frame count, not a fixed time

**Symptom.** Shake feels right on your dev machine but too fast, too slow, or too
short on a player's monitor with a different refresh rate.

**Cause.** Loops like `for i in range(10): offset = random(); await get_tree().process_frame`
tie the shake's duration to frame count, not real time. At 60 FPS that's ~166ms; at
144 FPS it's ~69ms — the same code produces a visibly different shake depending on
the display.

**Fix.** Drive the decay off `delta`, as in cause #2's `lerp(_shake_strength, 0.0,
_shake_decay * delta)` — the shake takes the same wall-clock time regardless of
frame rate, because `delta` shrinks to compensate on faster monitors.

## What all four have in common

Every case comes down to the same thing: `offset` is a single shared value, and
shake logic that doesn't own it exclusively — through direct writes, competing
tweens, or frame-count timing — ends up fighting something else that also touches
the camera. Route shake through one decaying value, keep it separate from whatever
sets `position`, and reset it on exit.

If you'd rather skip writing (and re-debugging) this yourself, that's exactly what
Saltmire Impact wraps into a single call — shake, hit-stop, flash and damage
numbers combined into tunable combos that don't step on your own camera-follow code.
