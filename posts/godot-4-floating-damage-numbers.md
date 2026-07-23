---
title: How to make floating damage numbers in Godot 4 (pooled, no lag)
description: A step-by-step Godot 4 tutorial for floating combat damage numbers — a reusable Label scene, a pooled spawner that never allocates on the hot path, and juice like crits and knockback-aware offsets.
slug: godot-4-floating-damage-numbers
date: 2026-07-23
product_name: Saltmire Hitbox
product_url: https://saltmire.itch.io/saltmire-hitbox
---

Floating damage numbers are one of the cheapest ways to make combat feel like it
*lands*. But the naive version — `instantiate()` a Label every hit — quietly thrashes
the garbage collector and stutters once a horde starts taking damage. Here's the
version that scales: a small reusable scene plus a pool that never allocates mid-fight.

## Step 1: the number scene

Make a scene with a single `Label` root, call it `DamageNumber`. Give it a script:

```gdscript
class_name DamageNumber extends Label

func show_value(value: int, crit := false) -> void:
    text = str(value)
    modulate = Color(1, 0.9, 0.3) if crit else Color.WHITE
    scale = Vector2.ONE * (1.4 if crit else 1.0)
    modulate.a = 1.0
```

Set the label's `horizontal_alignment` to Center in the inspector so it grows from
its middle. That's the whole visual — everything else is motion.

## Step 2: animate one number

A damage number does two things: drift up and fade out. Tween both in parallel, then
report back when it's done so the pool can reclaim it:

```gdscript
signal finished(node)

func play(at: Vector2) -> void:
    global_position = at
    var rise := at + Vector2(randf_range(-12, 12), -34)
    var t := create_tween().set_parallel()
    t.tween_property(self, "global_position", rise, 0.55) \
        .set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
    t.tween_property(self, "scale", Vector2.ONE, 0.18)   # settle the crit pop
    t.tween_property(self, "modulate:a", 0.0, 0.55).set_delay(0.15)
    t.chain().tween_callback(func(): finished.emit(self))
```

The small random x-jitter matters more than it looks: without it, ten hits on the same
enemy stack into one unreadable blur.

## Step 3: the pool (the part that actually matters)

Instead of creating and freeing labels, preallocate a handful and hand them out. When
one finishes, it goes back in the box:

```gdscript
extends Node2D

@export var scene: PackedScene           # DamageNumber.tscn
@export var pool_size := 24
var _free: Array[DamageNumber] = []

func _ready() -> void:
    for i in pool_size:
        var n: DamageNumber = scene.instantiate()
        n.hide()
        n.finished.connect(_reclaim)
        add_child(n)
        _free.append(n)

func spawn(value: int, at: Vector2, crit := false) -> void:
    var n: DamageNumber = _free.pop_back() if _free else _steal_oldest()
    n.show()
    n.show_value(value, crit)
    n.play(at)

func _reclaim(n: DamageNumber) -> void:
    n.hide()
    _free.append(n)
```

`pool_size` is the only tuning knob: it should be a little above the most numbers you
expect on screen at once. If the pool empties during a big burst, `_steal_oldest()`
recycles the number that's been alive longest — visually you never notice.

```gdscript
func _steal_oldest() -> DamageNumber:
    var n: DamageNumber = get_child(0)   # oldest live child
    move_child(n, get_child_count() - 1) # rotate it to the back
    return n
```

## Step 4: fire it from a hit

Wherever damage is applied — your hurtbox's `hurt` signal is the natural place — call
the spawner. Push crits and the hit direction through so the number can react:

```gdscript
func _on_hurt(damage: float, source: Node, knockback: Vector2) -> void:
    hp -= damage
    var crit := damage >= crit_threshold
    $DamageNumbers.spawn(int(damage), global_position + Vector2(0, -20), crit)
```

Offsetting slightly opposite the knockback (`- knockback.normalized() * 10`) makes the
number feel like it's popping *off* the hit rather than sitting on the sprite.

## That's the whole system

Preallocated pool, parallel rise-and-fade tween, crit color/scale, readable jitter —
that's floating damage numbers that hold up when the screen fills with enemies. If
you'd rather not wire the pool, the signal plumbing and the hit source by hand,
pooled damage numbers are one of the pieces already built into Saltmire Hitbox,
alongside the Hitbox2D/Hurtbox2D that emit the hit in the first place.
