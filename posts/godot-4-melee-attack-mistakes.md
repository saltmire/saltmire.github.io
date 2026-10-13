---
title: 7 Godot 4 melee attack mistakes (and the fix for each)
description: Seven common mistakes when building a melee attack in Godot 4 — always-on hitboxes, one swing hitting five times, hitting yourself, the "Function blocked during in/out signal" error, hitboxes that don't flip, damage in the wrong node and one-frame active windows — each with paste-able GDScript.
slug: godot-4-melee-attack-mistakes
date: 2026-10-13
product_name: Saltmire Hitbox
product_url: https://saltmire.itch.io/saltmire-hitbox
---

A melee attack in Godot 4 looks like a ten-minute job: put an `Area2D` on the sword,
listen for `area_entered`, subtract health. Then you playtest. The enemy dies from
standing next to you, one swing deals triple damage, the player hits themselves, and the
sword hitbox points right while the character faces left.

These are the seven mistakes behind almost every "my melee attack is broken" thread,
with the fix for each.

## 1. The hitbox is on all the time

If the sword's `Area2D` monitors every frame, anything that touches the sword takes
damage — including an enemy that just walked into you while you were idle. A hitbox
should only exist during the *active frames* of the attack.

```gdscript
# player.gd
@onready var sword_hitbox: Area2D = $Pivot/SwordHitbox

func _ready() -> void:
    sword_hitbox.monitoring = false

func attack() -> void:
    $AnimationPlayer.play("attack")
```

Then, in the `attack` animation, add a **Property track** on
`Pivot/SwordHitbox:monitoring`: key `true` on the frame the blade swings out, `false`
when it's done. The animation now owns the timing, which is where a designer will look
for it.

## 2. One swing hits the same enemy three times

`area_entered` fires every time an overlap *starts*. If the enemy's hurtbox has two
shapes, or the enemy gets knocked back and slides into the blade again, one swing lands
several hits. Keep a list of what this swing already hit and clear it when a new swing
starts:

```gdscript
# sword_hitbox.gd
extends Area2D

@export var damage := 10.0
var _hit_this_swing: Array[Area2D] = []

func _ready() -> void:
    area_entered.connect(_on_area_entered)

func start_swing() -> void:
    _hit_this_swing.clear()

func _on_area_entered(area: Area2D) -> void:
    if area in _hit_this_swing:
        return
    _hit_this_swing.append(area)
    if area.has_method("take_hit"):
        area.take_hit(damage, global_position)
```

Call `start_swing()` from a **Call Method** track on the first frame of the attack
animation, right before `monitoring` turns on.

## 3. The player hits themselves

The sword's `Area2D` overlaps the player's own hurtbox on the first frame of every
swing. Don't fix this with `if area.owner == self` checks scattered everywhere — fix it
in the collision bits. Put hurtboxes on team layers (`player_hurtbox`,
`enemy_hurtbox`) and give the player's sword a mask that only contains
`enemy_hurtbox`. The overlap never happens, so there's nothing to filter.

## 4. "Function blocked during in/out signal"

You try to turn the hitbox off the moment it hits something:

```gdscript
func _on_area_entered(area: Area2D) -> void:
    monitoring = false  # error!
```

Godot refuses, because you're changing physics state while the physics server is in the
middle of reporting overlaps. The error message tells you the fix:

```gdscript
func _on_area_entered(area: Area2D) -> void:
    set_deferred("monitoring", false)
```

The same applies to toggling `CollisionShape2D.disabled` from inside a body or area
signal — use `set_deferred("disabled", true)`.

## 5. The hitbox doesn't flip with the character

`Sprite2D.flip_h = true` mirrors the *picture*, not the child nodes. Your sword hitbox
stays on the right. Put everything that should mirror under a `Node2D` pivot and flip
that instead:

```gdscript
@onready var pivot: Node2D = $Pivot  # holds Sprite2D + SwordHitbox

func _physics_process(_delta: float) -> void:
    var dir := Input.get_axis("move_left", "move_right")
    if dir != 0.0:
        pivot.scale.x = sign(dir)
```

Flip the pivot, not the `CharacterBody2D` itself — a negative scale on a physics body
gets reset by the physics server and causes strange behaviour.

## 6. The damage logic lives in the sword

When the hitbox does `area.get_parent().health -= damage`, every attack in the game
needs to know how every target stores health, handles invincibility frames and reacts.
Flip the dependency: the hurtbox receives the hit and forwards it, and the receiver
decides what happens.

```gdscript
# hurtbox.gd
extends Area2D
signal hurt(amount: float, from_position: Vector2)

func take_hit(amount: float, from_position: Vector2) -> void:
    hurt.emit(amount, from_position)
```

The enemy connects `hurt` to its own health component, which can ignore the hit during
i-frames, apply resistances or trigger knockback. The sword stays dumb, and any new
attack — arrows, explosions, spikes — reuses the same hurtbox.

## 7. The active window is one frame long

A fast jab that enables `monitoring` for a single frame often misses. The new overlap is
picked up on the next physics step, and if your animation turns the hitbox off before
that step runs, the signal never fires. At 60 physics ticks per second, keep active
windows at **3+ physics frames** (about 0.05 s). If a design really needs a single-frame
hit, skip the signal and query directly:

```gdscript
func instant_hit() -> void:
    await get_tree().physics_frame
    for area in sword_hitbox.get_overlapping_areas():
        _on_area_entered(area)
```

## The pattern behind all seven

Every mistake above is the same thing in a different costume: a melee attack is not
"an Area2D on a sword", it's a small contract — *when* the box is live, *who* it can
see, *how many times* it may hit, and *who* decides what a hit means. Write that
contract once and every attack in your game gets it for free.

Saltmire Hitbox is that contract packaged as a `Hitbox2D` / `Hurtbox2D` pair for
Godot 4: `activate()` / `deactivate()` for active windows, a one-hit-per-swing option
with `reset()`, teams instead of hand-set collision bits, a helper that binds the
hitbox to specific `AnimatedSprite2D` frames, plus knockback and i-frames on the
receiving side. If you'd rather build it yourself, the seven fixes above are the core
of what it does.
