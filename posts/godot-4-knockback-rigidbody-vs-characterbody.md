---
title: RigidBody2D vs CharacterBody2D for knockback in Godot 4 — which and when
description: A practical Godot 4 comparison for implementing hit knockback — when to fake it on a CharacterBody2D, when to reach for a real RigidBody2D, and the hybrid trick most shipped games actually use.
slug: godot-4-knockback-rigidbody-vs-characterbody
date: 2026-08-20
product_name: Saltmire Hitbox
product_url: https://saltmire.itch.io/saltmire-hitbox
---

Every combat game needs knockback, and every combat game asks the same question at
some point: should the thing that just got hit be a `RigidBody2D`, or should you fake
the shove on the `CharacterBody2D` you already have? Both work. They fail in different
ways, and picking the wrong one costs you a rewrite mid-project.

## The CharacterBody2D approach: a velocity you decay

Most character controllers in Godot 4 are already `CharacterBody2D`, driven by
`move_and_slide()`. Knockback here means adding a temporary velocity on top of the
normal movement input and letting it bleed off over a few frames.

```gdscript
extends CharacterBody2D

var knockback := Vector2.ZERO
const KNOCKBACK_FRICTION := 900.0

func apply_knockback(direction: Vector2, force: float) -> void:
	knockback = direction.normalized() * force

func _physics_process(delta: float) -> void:
	var input_velocity := get_input_velocity() # your normal movement code

	knockback = knockback.move_toward(Vector2.ZERO, KNOCKBACK_FRICTION * delta)

	velocity = input_velocity + knockback
	move_and_slide()
```

This is cheap, deterministic, and stays inside `move_and_slide()`'s collision rules —
the body still slides along walls correctly while it's being pushed. The catch: it is
entirely your own simulation. There is no real physics response, so two bodies pushed
into each other don't interact, and the "weight" of a hit is whatever curve you hand-tune
into `KNOCKBACK_FRICTION`.

## The RigidBody2D approach: apply_impulse and let physics do it

A `RigidBody2D` gives you a real physics body — mass, impulses, collision response
between bodies for free.

```gdscript
extends RigidBody2D

func apply_knockback(direction: Vector2, force: float) -> void:
	apply_impulse(direction.normalized() * force)
```

That's the whole function. The physics engine handles the deceleration (via
`linear_damp`), the collisions with other rigid bodies, and bodies piling into each
other look and feel physical because they *are* physical. The catch: `RigidBody2D`
doesn't give you `move_and_slide()`-style character control. If your enemy or player
also needs precise, responsive movement input, you're now fighting the physics engine
for control of the same body, and that fight usually shows up as jitter against walls
or a character that "floats" a frame after landing.

## The comparison

| | CharacterBody2D (faked) | RigidBody2D (real) |
|---|---|---|
| Setup cost | one velocity field + `move_toward` | `apply_impulse` and done |
| Feel | fully tunable, but hand-rolled | physically consistent, less tunable |
| Body-to-body interaction | none — you'd have to script it | free, physics engine handles it |
| Movement input while knocked back | trivial to blend | fights the physics solver |
| Determinism | yes | mostly, minor solver variance |
| Good for | player character, most enemies | ragdolls, debris, crowds, destructibles |

## The hybrid most shipped games actually use

The honest answer is that neither option alone covers a whole game. The pattern that
holds up: keep your player and most enemies on `CharacterBody2D` with faked knockback,
because you need tight control over their movement every single frame. Switch to
`RigidBody2D` only for things that are *allowed* to lose control entirely — a dead
enemy's ragdoll, a barrel that goes flying, loose debris in a destructible wall.

A trick that gets you most of the RigidBody feel without giving up control: keep the
`CharacterBody2D`, but scale the knockback force by the target's own "weight" stat and
add a short window where player input is ignored so the hit actually reads:

```gdscript
var knockback_lock_timer := 0.0

func apply_knockback(direction: Vector2, force: float, weight: float = 1.0) -> void:
	knockback = direction.normalized() * (force / max(weight, 0.1))
	knockback_lock_timer = 0.12  # player input ignored for ~2 hit-stop frames

func _physics_process(delta: float) -> void:
	knockback_lock_timer = max(knockback_lock_timer - delta, 0.0)
	var input_velocity := Vector2.ZERO if knockback_lock_timer > 0.0 else get_input_velocity()

	knockback = knockback.move_toward(Vector2.ZERO, KNOCKBACK_FRICTION * delta)
	velocity = input_velocity + knockback
	move_and_slide()
```

That `weight` parameter is the part people skip and then wonder why every enemy flies
the same distance regardless of size.

## The number that actually decides it

If the object needs to respond to player input on the same frame it's simulating physics,
it's a `CharacterBody2D` with faked knockback — no exceptions, because fighting the
physics solver for input responsiveness is a losing, ongoing cost. If the object never
takes player input again after the hit (a corpse, debris, a thrown prop), it's a
`RigidBody2D` and you get the physics for free.

Wiring this up by hand means a `direction`, a `force`, a `weight`, teams so you don't
knock back your own allies, and i-frames so one hit doesn't chain into five — all before
you've written a single line of actual combat design. Saltmire Hitbox ships that whole
layer as a drop-in Hitbox2D / Hurtbox2D pair, knockback included, so the comparison
above is a five-minute decision instead of a rewrite.
