---
title: "Fixing 'previously freed instance' errors in Godot 4 combat code"
description: Godot 4 crashing with "previously freed instance" or "Cannot call method on a null value" when enemies die, or enemies dying twice? The 4 real causes in Godot 4 combat code (stale target references, await, same-frame double hits, get_parent() chains) and the exact fix for each.
slug: godot-4-previously-freed-instance-error
date: 2026-10-05
product_name: Saltmire Hitbox
product_url: https://saltmire.itch.io/saltmire-hitbox
---

Combat is where Godot 4 projects start crashing for the first time. Everything works
until two things die in the same frame, or a homing bullet outlives its target, and the
debugger stops on one of these:

- `Trying to call a function on a previously freed instance.`
- `Invalid access to property or key 'global_position' on a base object of type 'previously freed'.`
- `Cannot call method 'take_damage' on a null value.`
- `Resumed function 'flash()' after await, but class instance is gone.`

(Exact wording shifts a little between 4.x versions — older builds say
`Invalid get index ... (on base: 'previously freed')` — but the causes are the same.)

"Previously freed" means your variable still points at a node that `queue_free()` already
deleted. The reference isn't `null` — it's a dangling pointer, so `if target:` and
`if target != null:` can both let it through. Here are the four ways combat code ends up
holding one, ordered by how often they show up.

## 1. A stored reference outlives the enemy

**Symptom.** A homing projectile, a turret or an enemy AI crashes a few frames after
its target dies.

**Cause.** You saved the target in a variable (`var target: Node2D`) and kept using it.
Something else killed the target and called `queue_free()`. Your variable never heard
about it.

**Fix.** Check `is_instance_valid()` before every use — it's the only check that catches
a freed node:

```gdscript
var target: Node2D

func _physics_process(delta: float) -> void:
    if not is_instance_valid(target):
        target = null
        _pick_new_target()
        return
    var dir := global_position.direction_to(target.global_position)
    velocity = dir * speed
    move_and_slide()
```

If many systems track the same enemy, clear the reference at the source instead of
checking everywhere. `tree_exiting` fires right before the node leaves the tree:

```gdscript
func set_target(t: Node2D) -> void:
    target = t
    t.tree_exiting.connect(func(): target = null, CONNECT_ONE_SHOT)
```

## 2. The reference is used again after an `await`

**Symptom.** Hit-flash or knockback code crashes only sometimes, usually on the killing
blow.

**Cause.** `await` pauses your function. Anything can happen while it's paused —
including the enemy dying. When the function resumes, every node reference captured
before the `await` is suspect.

```gdscript
# crashes when the hit also kills the enemy
func hit_flash(enemy: Node2D) -> void:
    enemy.modulate = Color.RED
    await get_tree().create_timer(0.1).timeout
    enemy.modulate = Color.WHITE   # enemy may be gone by now
```

**Fix.** Treat every `await` as a checkpoint and re-validate after it:

```gdscript
func hit_flash(enemy: Node2D) -> void:
    enemy.modulate = Color.RED
    await get_tree().create_timer(0.1).timeout
    if not is_instance_valid(enemy):
        return
    enemy.modulate = Color.WHITE
```

Even better: put the flash on the enemy itself, as a tween on its own sprite. A tween
created with the node's `create_tween()` is bound to that node and dies with it, so there
is nothing left to resume.

## 3. Two hits land in the same physics frame — the enemy dies twice

**Symptom.** No crash, but a shotgun blast drops double XP, plays the death sound twice,
or increments the kill counter by two.

**Cause.** `queue_free()` doesn't delete immediately — it deletes at the end of the frame.
If two bullets overlap the enemy in the same frame, both callbacks run while the node is
still perfectly valid, and both see `hp <= 0`.

**Fix.** Guard the death path with a flag (or `is_queued_for_deletion()`):

```gdscript
var dead := false

func take_damage(amount: float) -> void:
    if dead:
        return
    hp -= amount
    if hp <= 0.0:
        dead = true
        died.emit()
        drop_xp()
        queue_free()
```

Bullets that hit should also stop themselves right away — `set_deferred("monitoring", false)`
then `queue_free()` — so a single bullet can't register on two enemies in its last frame.

## 4. `get_parent()` chains return something you didn't expect

**Symptom.** `Cannot call method 'take_damage' on a null value`, or
`Nonexistent function 'take_damage' in base 'Area2D'`.

**Cause.** The attacker reaches into the victim:
`area.get_parent().take_damage(10)`. That works until one enemy has its hurtbox nested
one level deeper, or the parent is a pooled node that's already been detached.

**Fix.** Don't make the attacker know the victim's tree. Check the contract instead of
the shape:

```gdscript
func _on_area_entered(area: Area2D) -> void:
    var victim := area.owner
    if is_instance_valid(victim) and victim.has_method("take_damage"):
        victim.take_damage(damage)
```

## The pattern that removes most of these

Notice what causes 1, 2 and 4 have in common: the **attacker** holds a reference to the
**victim** and calls into it. Flip that around and most of the bugs disappear. The
attacker only overlaps an area; the victim's own hurtbox emits a signal; the victim
handles its own damage, death and flash. When the victim is freed, its signal
connections go with it — nobody is left holding a stale pointer.

```gdscript
# on the enemy — it owns its own death
func _ready() -> void:
    $Hurtbox.hurt.connect(_on_hurt)

func _on_hurt(amount: float, _source: Node, knockback: Vector2) -> void:
    take_damage(amount)
    velocity += knockback
```

That's exactly the shape Saltmire Hitbox is built around: drop a `Hitbox2D` on the attack
and a `Hurtbox2D` on anything that can be hurt, and damage arrives as a `hurt` signal on
the victim's side. The hitbox never calls into your enemy's script, `one_shot` stops a
lingering swing from hitting the same target every frame, and i-frames are one inspector
field. You still want the `dead` flag from cause 3 in your own death code — but the
dangling-reference class of crashes mostly stops existing.
