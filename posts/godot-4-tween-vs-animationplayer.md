---
title: "Tween vs AnimationPlayer in Godot 4 — which to use and when"
description: Tween and AnimationPlayer both animate values in Godot 4, but they solve different problems. Here's a clear comparison table, real code for each, and a verdict so you pick the right tool the first time.
slug: godot-4-tween-vs-animationplayer
date: 2026-07-14
product_name: Saltmire Juice
product_url: https://saltmire.itch.io/saltmire-juice
---

Both `Tween` and `AnimationPlayer` animate values in Godot 4. Both can move, fade,
scale, and colour things. If you've ever stared at a new node and wondered which one
to reach for, here's the honest breakdown.

## Quick comparison

| | Tween | AnimationPlayer |
|---|---|---|
| Lives in | code (`create_tween()`) | a node in the scene tree |
| Keyframes | no — set target value + duration | yes, visual timeline editor |
| Multi-property tracks | no (chains, not tracks) | yes |
| Blend / cross-fade | no | yes, via `AnimationTree` |
| Reacts to runtime values | yes — target set in code | harder, needs manual sync |
| Easing / curves | built-in enums | curve editor |
| Restartable mid-flight | yes — `kill()` + new tween | yes — `stop()` + `play()` |
| Scene export | not really | yes, included in `.tscn` |
| Best for | juice, reactive effects, one-shot polish | locomotion, cutscenes, multi-track sync |

## When Tween wins: reactive, code-driven effects

Tween is not a node. You call `create_tween()` and it runs and frees itself — no
leftover scene nodes, no cleanup. That makes it the right tool for short, reactive
effects where the target value is only known at runtime.

**Pop-scale on hit:**

```gdscript
func pop(target: Node2D) -> void:
    var tw := create_tween()
    tw.tween_property(target, "scale", Vector2(1.35, 1.35), 0.08) \
        .set_ease(Tween.EASE_OUT)
    tw.tween_property(target, "scale", Vector2.ONE, 0.14) \
        .set_trans(Tween.TRANS_ELASTIC).set_ease(Tween.EASE_OUT)
```

**Slide a UI panel in from a dynamic off-screen position:**

```gdscript
func slide_in(panel: Control, start_x: float) -> void:
    panel.position.x = start_x
    var tw := create_tween()
    tw.tween_property(panel, "position:x", 0.0, 0.3) \
        .set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
```

**Fade and free a damage number:**

```gdscript
func float_number(label: Label, value: int) -> void:
    label.text = str(value)
    var tw := create_tween().set_parallel(true)
    tw.tween_property(label, "position:y", label.position.y - 40, 0.6)
    tw.tween_property(label, "modulate:a", 0.0, 0.5).set_delay(0.1)
    tw.chain().tween_callback(label.queue_free)
```

Tweens are also chainable (`.chain()`) and parallelizable (`.set_parallel(true)`),
so you can sequence multi-step effects entirely in code without an editor.

## When AnimationPlayer wins: authored sequences and character animation

AnimationPlayer is a node you add to the scene. Open the Animation panel, and every
property on any child node can be a keyframe. That makes it the right tool for
anything you want to *edit visually* — especially when more than two properties move
in sync, or when animations need to blend.

**A melee attack that moves the body, flashes the sprite, and emits a particle:**

```gdscript
func attack() -> void:
    $AnimationPlayer.play("attack")
    await $AnimationPlayer.animation_finished
    _return_to_idle()
```

All the timing lives in the authored clip. Tweak it in the editor without touching
code.

**Blended locomotion (walk → run → idle):**

Add an `AnimationTree` on top of `AnimationPlayer` and build a state machine or
blend space — then drive it from code with a single float:

```gdscript
$AnimationTree.set("parameters/blend_position", velocity.length() / max_speed)
```

That cross-fade would take hundreds of lines to replicate with tweens.

## The rule of thumb

> **Reach for Tween** when the target value is decided at runtime, the effect is
> under ~0.5 s, and it's self-contained (scale pop, slide in, fade out, number float).
>
> **Reach for AnimationPlayer** when you want to edit the sequence visually, more
> than two properties move together, or animations need to blend.

Most games use both: AnimationPlayer for character locomotion and cutscenes, Tweens
for every piece of reactive UI juice.

## Godot 4 vs Godot 3: the one breaking change

In Godot 3, `Tween` was a node you added to the scene tree. In Godot 4 it's
instantiated with `create_tween()` directly on a `Node` (or `get_tree().create_tween()`
if you're outside a node). There are no more stale tween nodes dangling in your tree.
If you're porting from Godot 3, that's the only real rewire needed.

## If you want the juice without the wiring

Screen shake, hit-stop, floating damage numbers, and sprite flash are the most
common tween-based juice effects every action game needs. If you'd rather not
re-derive each one per project, **Saltmire Juice** is a free, MIT-licensed add-on
that ships all of them as one-call autoloads — `Juice.shake()`, `Juice.hit_stop()`,
`Juice.damage_number()` — drop it in and move on.
