---
title: What I learned building a health component with i-frames in Godot 4
description: Lessons from building a reusable health and damage component in Godot 4 — why health belongs in its own node, the double-hit bug i-frames actually fix, and why "died" must only fire once.
slug: godot-4-health-component-iframes
date: 2026-09-25
product_name: Saltmire Hitbox
product_url: https://saltmire.itch.io/saltmire-hitbox
---

Every Godot 4 project I start ends up with `var health := 100` pasted into the player, then
the enemy, then the breakable crate. Then the three copies drift apart. Here is what I
learned pulling health out into one reusable component, roughly in the order each bug
showed up.

## Lesson 1: health is not the player's job

The first version always lives inside the player script:

```gdscript
var health := 100

func take_damage(amount: int) -> void:
	health -= amount
	if health <= 0:
		die()
```

That's fine until an enemy needs the same logic, then a destructible barrel, then a boss
with a health bar. Once there are three copies, one gets clamping, one gets a signal for
the UI, and one gets neither. The fix is a small node you can drop into any scene:

```gdscript
class_name HealthComponent
extends Node

signal health_changed(current: int, max_health: int)
signal died

@export var max_health := 100
var current := max_health

func _ready() -> void:
	current = max_health

func damage(amount: int) -> void:
	current = clampi(current - amount, 0, max_health)
	health_changed.emit(current, max_health)
	if current == 0:
		died.emit()

func heal(amount: int) -> void:
	current = clampi(current + amount, 0, max_health)
	health_changed.emit(current, max_health)
```

The owner (player, enemy, crate) connects to `died` and decides what death *means*. The
component only counts. That split turned out to matter more than any of the code.

## Lesson 2: the health bar should never ask for health

My early UI code read `player.health` every frame in `_process`. That works, but it ties
the health bar to one specific node and breaks the moment the player is freed and
respawned. With the signal, the bar just listens:

```gdscript
func bind(health: HealthComponent) -> void:
	health.health_changed.connect(_on_health_changed)
	_on_health_changed(health.current, health.max_health)

func _on_health_changed(current: int, max_health: int) -> void:
	value = float(current) / max_health * 100.0
```

Calling the handler once inside `bind()` is the part I kept forgetting. Without it the bar
shows 100% until the first hit, even if the scene loaded with the player at half health.

## Lesson 3: the double-hit bug is what i-frames actually fix

I thought invincibility frames were a design choice, something that makes the game feel
fairer. In practice they fixed a real bug first. A spike hitbox overlapping the player
for 12 physics frames dealt damage 12 times, and a single sword swing could hit twice
when the enemy's hurtbox entered, left, and re-entered the area during the animation.

A timer inside the component fixes both at the source:

```gdscript
@export var iframe_duration := 0.5
var _invulnerable := false

func damage(amount: int) -> void:
	if _invulnerable or current == 0:
		return
	current = clampi(current - amount, 0, max_health)
	health_changed.emit(current, max_health)
	if current == 0:
		died.emit()
		return
	if iframe_duration > 0.0:
		_invulnerable = true
		get_tree().create_timer(iframe_duration).timeout.connect(
			func(): _invulnerable = false)
```

Enemies in a horde game usually want `iframe_duration = 0.0` (or something very short)
so fast weapons still feel fast. The player usually wants 0.5–1.0 seconds. Making it an
export instead of hard-coding it was what let one component work for both.

## Lesson 4: "died" must fire exactly once

This bug wasted an evening. Two projectiles hit an enemy on the same physics frame. Both
called `damage()`, both saw `current == 0` afterwards, and `died` fired twice. The enemy
dropped two coins, the kill counter went up by two, and the second `queue_free()` threw
an error on an instance that was already queued.

That's why the check at the top of `damage()` has `or current == 0`. Once health reaches
zero, the component ignores everything after it. It's one condition, and it's also the
only place that condition needs to exist. Anything listening to `died` can assume it runs
once per life.

If you add a respawn, give it an explicit reset instead of healing from zero:

```gdscript
func reset() -> void:
	current = max_health
	_invulnerable = false
	health_changed.emit(current, max_health)
```

`heal()` on a dead entity was the other source of zombies. I made healing from 0 do
nothing, and revival only happens on purpose.

## Lesson 5: flash the sprite from the owner, not the component

The component should not know there's a sprite. When I put `modulate` changes inside it,
it broke immediately on the crate, which used a different node structure. Now the owner
reacts to the signal it already has:

```gdscript
func _ready() -> void:
	$HealthComponent.health_changed.connect(func(_c, _m): _flash())

func _flash() -> void:
	var t := create_tween()
	$Sprite2D.modulate = Color(1, 0.4, 0.4)
	t.tween_property($Sprite2D, "modulate", Color.WHITE, 0.15)
```

## What I'd do differently starting over

Build the component first, before the second thing that can take damage exists. Put
i-frames and the "dead means dead" guard in from day one, because both bugs show up the
first time two hits land close together. And keep the component dumb: it counts, emits,
and refuses. Everything visual belongs to whoever owns it.

The part this post skips is the other half: *who* is allowed to hit *whom*. That's
collision layers, teams, making sure the player's own sword doesn't hurt the player, and
knockback direction. That's the wiring I got tired of redoing in every project.
