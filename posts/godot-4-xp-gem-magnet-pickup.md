---
title: How to make XP gems with a pickup magnet and level-up bar in Godot 4
description: A step-by-step Godot 4 tutorial for survivors-style experience pickups — gems that drop from enemies, get pulled toward the player by a magnet radius, and fill an XP bar with a rising level curve.
slug: godot-4-xp-gem-magnet-pickup
date: 2026-10-11
product_name: Survivors Template
product_url: https://saltmire.itch.io/survivors-template-godot
---

Every survivors-like has the same small loop: an enemy dies, a gem drops, you walk near it,
it flies into you, the XP bar ticks up. It looks like nothing, but a big part of the
satisfaction comes from that loop. Get it wrong and pickups feel sticky or laggy, or they
tank the frame rate once 300 gems are lying on the floor.

This tutorial builds it in Godot 4: an XP gem scene, a magnet area on the player, a smooth
pull that speeds up, and an `XP` component with a level curve that a UI bar can listen to.

## Step 1: the gem scene

Create `xp_gem.tscn` with this tree:

- `XPGem` (**Area2D**)
  - `Sprite2D`
  - `CollisionShape2D` (small circle, radius ~6)

Put the gem on its own physics layer, for example layer 5 "pickups", with **no mask**.
The gem doesn't need to detect anything. The player's areas will detect *it*.

```gdscript
# xp_gem.gd
extends Area2D

@export var value := 1

var target: Node2D = null
var speed := 0.0

const ACCEL := 900.0      # px/s² — how fast the pull ramps up
const MAX_SPEED := 700.0

func attract(to: Node2D) -> void:
	if target == null:
		target = to

func _physics_process(delta: float) -> void:
	if target == null:
		return
	if not is_instance_valid(target):
		target = null
		return
	speed = min(speed + ACCEL * delta, MAX_SPEED)
	global_position = global_position.move_toward(target.global_position, speed * delta)
```

The acceleration is the important part. A constant speed looks robotic. Starting at zero
and ramping up gives the little "pop then whoosh" players expect.

## Step 2: two areas on the player

The player needs **two** Area2D children, both with mask = layer 5:

- `MagnetArea`: big circle (radius ~80). It decides *when* a gem starts flying.
- `CollectArea`: small circle (radius ~12). It decides *when* a gem is absorbed.

Keeping them separate lets you upgrade the magnet radius without changing how close a gem
has to get before it counts.

```gdscript
# player.gd (relevant part)
extends CharacterBody2D

@onready var magnet_shape: CollisionShape2D = $MagnetArea/CollisionShape2D
@onready var xp: XPComponent = $XPComponent

func _ready() -> void:
	$MagnetArea.area_entered.connect(_on_magnet_area_entered)
	$CollectArea.area_entered.connect(_on_collect_area_entered)

func _on_magnet_area_entered(area: Area2D) -> void:
	if area.has_method("attract"):
		area.attract(self)

func _on_collect_area_entered(area: Area2D) -> void:
	if area.has_method("attract"):
		xp.add(area.value)
		area.queue_free()

func set_magnet_radius(r: float) -> void:
	(magnet_shape.shape as CircleShape2D).radius = r
```

One gotcha: shapes are shared resources. If several scenes use the same `CircleShape2D`,
growing it on one player grows it on all of them. Tick **Local to Scene** on the shape (or
`duplicate()` it in `_ready`) before changing the radius at runtime.

## Step 3: drop gems when enemies die

In your enemy's death code, spawn the gem with `call_deferred`. Death usually happens
inside a physics callback, and adding an Area2D during one triggers the
"Can't change this state while flushing queries" error.

```gdscript
# enemy.gd
const GEM := preload("res://xp_gem.tscn")

@export var xp_value := 1

func die() -> void:
	var gem := GEM.instantiate()
	gem.value = xp_value
	gem.global_position = global_position
	get_tree().current_scene.add_child.call_deferred(gem)
	queue_free()
```

## Step 4: the XP component and level curve

Keep the numbers out of the player script. A small component does the math and only
emits signals, so the UI, the upgrade screen and the audio can each react on their own.

```gdscript
# xp_component.gd
class_name XPComponent
extends Node

signal xp_changed(current: int, needed: int)
signal leveled_up(new_level: int)

@export var base_needed := 5
@export var growth := 1.25   # each level needs 25% more

var level := 1
var current := 0

func needed_for(lvl: int) -> int:
	return int(round(base_needed * pow(growth, lvl - 1)))

func add(amount: int) -> void:
	current += amount
	# while, not if: one big gem can be worth several levels
	while current >= needed_for(level):
		current -= needed_for(level)
		level += 1
		leveled_up.emit(level)
	xp_changed.emit(current, needed_for(level))
```

That `while` is the most common bug in hand-rolled XP code. With `if`, a gem worth 40 XP at
level 1 gives one level and leaves the bar over 100%.

## Step 5: the XP bar

A `ProgressBar` (or `TextureProgressBar`) at the top of the screen, driven only by the
signal:

```gdscript
# xp_bar.gd
extends ProgressBar

@export var xp_path: NodePath

func _ready() -> void:
	var xp: XPComponent = get_node(xp_path)
	xp.xp_changed.connect(_on_xp_changed)
	_on_xp_changed(xp.current, xp.needed_for(xp.level))

func _on_xp_changed(current: int, needed: int) -> void:
	max_value = needed
	create_tween().tween_property(self, "value", current, 0.15)
```

The short tween makes the bar slide instead of snap. On level-up it drops back toward zero
and refills, so the player can actually see it happen.

## Step 6: survive 300 gems on screen

Late in a run, gems pile up faster than the player collects them. Three cheap fixes:

- **Merge on the floor.** If more than ~150 gems exist, spawn the new one's value into the
  nearest existing gem instead of creating another node.
- **Don't run idle gems.** Call `set_physics_process(false)` in the gem's `_ready()` and
  turn it back on in `attract()`. Then only gems that are flying cost anything per frame.
- **Vacuum pickup.** A rare drop that calls `attract(player)` on every node in a `"gems"`
  group clears the floor and feels great.

## Wrapping up

That's the whole loop: gem drops, magnet pull with acceleration, collect, XP curve with a
`while`, bar that tweens. What usually comes next is the level-up draft (pick 1 of 3
upgrades), weapons that scale with it, and waves that ramp up. That's where a small
prototype turns into a lot of systems to keep in sync. If you'd rather start from a
version where all of that is already wired together and data-driven, the Saltmire Survivors
Template ships it as a playable Godot 4 project.
