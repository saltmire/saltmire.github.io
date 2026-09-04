---
title: What I learned building an enemy state machine in Godot 4
description: Lessons from building an enemy state machine in Godot 4 — why a match statement stops scaling, the transition bug that only shows up under pressure, and what actually earns its own State node.
slug: godot-4-enemy-state-machine
date: 2026-09-04
product_name: Survivors Template
product_url: https://saltmire.itch.io/survivors-template-godot
---

I wrote "just use a match statement, it's fine" three times before I stopped saying it. It
is fine, right up until an enemy needs a fourth state and two of the transitions start
depending on each other. Here is what actually cost time building enemy AI for a
wave-based game, in the order it bit me.

## Lesson 1: the match statement is fine until state 4

A two-state enemy — chase, attack — is genuinely not worth a framework:

```gdscript
func _physics_process(delta: float) -> void:
	match state:
		State.CHASE:
			velocity = (player.global_position - global_position).normalized() * speed
			if global_position.distance_to(player.global_position) < attack_range:
				state = State.ATTACK
		State.ATTACK:
			attack_timer -= delta
			if attack_timer <= 0.0:
				do_attack()
				state = State.CHASE
```

The moment a third and fourth state show up — hurt, dead, stagger, windup — the match
block stops being one enemy's logic and becomes a grid of every state times every other
state it might transition to. That grid is where the bugs live, not in any single state.

## Lesson 2: the bug is never inside a state, it's in the transition

Every state-machine bug I actually spent time on was the same shape: state A left some
flag or timer set that state C didn't know to check. An enemy stuck mid-attack-animation
forever, still receiving hits, was not a bug in the attack state — it was the hurt state
interrupting attack without cleaning up `attack_timer` or resetting the animation.

The fix that made these bugs findable is giving every state an explicit `enter` and
`exit`, and never mutating another state's data directly:

```gdscript
func change_state(new_state: State) -> void:
	if new_state == state:
		return
	_exit_state(state)
	state = new_state
	_enter_state(new_state)

func _exit_state(s: State) -> void:
	match s:
		State.ATTACK:
			attack_timer = 0.0
			sprite.stop()

func _enter_state(s: State) -> void:
	match s:
		State.HURT:
			velocity = Vector2.ZERO
			hurt_timer = HURT_DURATION
			sprite.play("hurt")
```

One entry point for every transition means you can put a single `print` in
`change_state` and see the entire life of an enemy in the log, instead of guessing which
of six scattered `state = X` lines fired.

## Lesson 3: a Node-per-state is not overkill once you have more than one enemy type

I resisted the State-as-a-Node pattern for a long time — it felt like ceremony for
something a match statement already did. It earns its cost the moment you have more than
one enemy *type* sharing behavior: a ranged enemy and a melee enemy both need chase and
hurt, but attack is completely different.

```gdscript
class_name EnemyState
extends Node

func enter(_enemy: Node) -> void: pass
func exit(_enemy: Node) -> void: pass
func physics_update(_enemy: Node, _delta: float) -> void: pass

class_name ChaseState
extends EnemyState

func physics_update(enemy: Node, delta: float) -> void:
	enemy.velocity = enemy.direction_to_player() * enemy.speed
	if enemy.in_attack_range():
		enemy.state_machine.change_to("attack")
```

Now `attack` is swappable per enemy scene without touching `chase` or `hurt` at all. For
a single enemy type, this is genuinely more code than a match statement for no benefit —
the crossover point is real, not just taste.

## Lesson 4: "dead" is a state too, and it needs to block every other transition

The bug that took longest to track down: an enemy could take lethal damage, enter
`hurt`, and the hurt-state's timer would flip it back to `chase` — bringing a corpse back
to life for one frame before `queue_free()` caught up. `dead` was handled as an
`if health <= 0: queue_free()` check scattered in three places instead of being a real
state in the machine.

```gdscript
func take_damage(amount: int) -> void:
	health -= amount
	if health <= 0:
		change_state(State.DEAD)   # one path in, nothing else can override it
		return
	change_state(State.HURT)
```

Once `dead` was a state like any other — with its own `enter()` that disables the
hitbox, stops physics, and plays the death animation before freeing — the flicker-back-
to-life bug had nowhere left to come from.

## What I'd do differently starting over

Start with the match statement — it is not a mistake, it is correctly the cheapest thing
that works for two or three states. Move to per-state nodes only when a second enemy
*type* needs to reuse half the states, not before. And treat `dead` as a first-class
state from the start; bolting it on as a health check scattered across the codebase is
where the worst bugs hide.

None of this is really about state machines. It's about giving every transition exactly
one door in and one door out, so that when an enemy does something wrong, there is
exactly one function to put a breakpoint in.
