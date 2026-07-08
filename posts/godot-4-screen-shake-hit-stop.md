---
title: Godot 4 screen shake and hit-stop in one script
description: Add punchy screen shake and hit-stop (freeze frames) to your Godot 4 game with a small, reusable Camera2D script — with tunable code you can paste in today.
slug: godot-4-screen-shake-hit-stop
date: 2026-07-07
product_name: Saltmire Impact
product_url: https://saltmire.itch.io/saltmire-impact
---

"Game feel" is mostly a handful of cheap effects stacked on top of otherwise
normal gameplay. Two of the highest-impact ones are **screen shake** and
**hit-stop**. Here is how to do both in Godot 4 with code you can reuse.

## Screen shake on a Camera2D

The trick is to offset the camera by a random amount each frame and decay that
amount over time. Attach this to your `Camera2D`:

```gdscript
extends Camera2D

var _trauma := 0.0        # 0..1, how much shake is queued
var _decay := 4.0         # how fast it fades per second
var _max_offset := 12.0   # pixels at full trauma

func shake(amount: float) -> void:
    _trauma = min(_trauma + amount, 1.0)

func _process(delta: float) -> void:
    if _trauma <= 0.0:
        offset = Vector2.ZERO
        return
    _trauma = max(_trauma - _decay * delta, 0.0)
    var t := _trauma * _trauma           # square it: small hits stay subtle
    offset = Vector2(
        randf_range(-1, 1) * _max_offset * t,
        randf_range(-1, 1) * _max_offset * t
    )
```

Call `camera.shake(0.4)` on a hit. Squaring the trauma (`t = _trauma * _trauma`)
is what makes it feel good — light hits barely nudge, big hits kick hard.

## Hit-stop (freeze frames)

Hit-stop briefly freezes the game on impact so a hit reads as *heavy*. In Godot 4
you scale `Engine.time_scale` down, wait, then restore it. Use an unscaled timer
so the freeze itself is not slowed:

```gdscript
func hit_stop(duration := 0.08, scale := 0.05) -> void:
    Engine.time_scale = scale
    # ignore_time_scale so the wait runs in real time
    await get_tree().create_timer(duration, true, false, true).timeout
    Engine.time_scale = 1.0
```

`await hit_stop()` on a big hit. Keep it short — 60–120 ms is plenty. Longer than
that and the game feels laggy instead of punchy.

## Stacking them

A satisfying hit usually fires several of these at once: shake + hit-stop + a
white flash on the sprite + damage numbers + a little particle burst. Each is a
few lines, but wiring all of them, tuned, for every hit type — light hit, heavy
hit, crit, death — is where the boilerplate piles up.

```gdscript
func on_enemy_hit(enemy, damage):
    camera.shake(0.3)
    await hit_stop()
    flash(enemy.sprite)
    spawn_damage_number(enemy.global_position, damage)
    # ...and a particle burst, and sound, per hit type
```

## Skip the wiring

The individual effects are free to build. If you would rather call one function —
`Impact.hit(enemy, "heavy")` — and get shake, curved hit-stop, flash, damage
numbers and shader FX in tuned combos, that is what Saltmire Impact is. The
building-block pieces (Juice, FX, Trail, Spark) are free and open source; Impact
is the orchestrator that ties them together.
