---
title: "Godot 4 hitbox and hurtbox the easy way (damage, teams, i-frames, knockback)"
description: How to build a clean hitbox/hurtbox system in Godot 4 with Area2D — collision layers and masks explained, plus damage, teams to stop friendly fire, invincibility frames and knockback, with copy-paste code.
slug: godot-4-hitbox-hurtbox
date: 2026-07-12
product_name: Saltmire Hitbox
product_url: https://saltmire.itch.io/saltmire-hitbox
---

Almost every action game needs the same thing: something that deals damage, and
something that takes it. In Godot 4 the raw tools are `Area2D` + `CollisionShape2D`,
but wiring them into a real hit is where people get stuck — collision layers vs
masks, stopping the player from hurting itself, not draining a target every physics
frame, and adding knockback and invincibility. Here's the whole thing, cleanly.

## The idea: two areas, opposite jobs

- A **Hitbox** is an `Area2D` on your attack (a sword swing, a bullet, a stomp).
  It only *scans* — it never needs to be detected.
- A **Hurtbox** is an `Area2D` on anything that can be damaged. It only needs to
  be *detected* — it never scans.

That split is the trick most tutorials skip, and it's why layers get confusing.

## Layers vs masks, in one sentence

`collision_layer` is *what you are*; `collision_mask` is *what you look for*. So:

```gdscript
# hurtbox: I exist on layer 20, and I look for nothing.
collision_layer = 0
set_collision_layer_value(20, true)
collision_mask = 0
monitorable = true
monitoring = false

# hitbox: I exist on nothing, and I look for layer 20.
collision_layer = 0
collision_mask = 0
set_collision_mask_value(20, true)
monitoring = true
```

Now a hitbox sees hurtboxes and *only* hurtboxes — no stray collisions with
walls or bodies. Pick any free bit; 20 is just an example.

## Teams (so the player doesn't hit itself)

Give each box a `team` integer and refuse same-team hits:

```gdscript
func _on_area_entered(area):
    if area is Hurtbox and area.team != team:
        area.receive(damage, self)
```

## The bug nobody warns you about: overlapping-on-activate

`area_entered` only fires when two areas *start* overlapping. If your hitbox turns
on while it's already sitting on top of the target — very common for a melee swing —
the signal never fires and the hit is silently lost. Fix it by also scanning what's
already inside when the swing starts:

```gdscript
func activate():
    active = true
    for area in get_overlapping_areas():
        _try_hit(area)
```

## Invincibility frames and knockback

After a hit, ignore further hits for a moment, and push the target away:

```gdscript
func receive(damage, source):
    if _invincible: return
    var dir = (global_position - source.global_position).normalized()
    hurt.emit(damage, dir * knockback_strength)
    if invincible_time > 0.0:
        _invincible = true
        get_tree().create_timer(invincible_time).timeout.connect(
            func(): _invincible = false)
```

That's a complete, correct hitbox/hurtbox: layers handled, friendly fire blocked,
no lost melee hits, i-frames and knockback in place.

## Skip the boilerplate

If you'd rather drop in two nodes and move on, **Saltmire Hitbox** packages exactly
this — `Hitbox2D` / `Hurtbox2D` with zero layer setup, plus damage types, crits,
per-type resistances, animation-frame timing and a runtime debug overlay. There's a
free MIT **Lite** core too if you just want the basics.
