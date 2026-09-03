---
title: What a survivors-like actually needs in Godot 4 — and what you can skip
description: The five systems that decide whether a Vampire Survivors-like in Godot 4 ships or stalls — data-driven waves, enemy count, the upgrade draft, honest damage, and meta progression — with the code for each and an honest note on what you can leave out.
slug: godot-4-survivors-like-systems
date: 2026-09-03
product_name: Survivors Template
product_url: https://saltmire.itch.io/survivors-template-godot
---

A survivors-like looks like the easiest genre to build. The player moves, the weapons
fire themselves, the enemies walk straight at you. You can have that on screen in a
weekend, and most people do.

Then it stalls. Not because the loop is hard, but because the five systems *around*
the loop are where the whole genre actually lives. Here is what each one has to do,
what it costs you, and the two things everybody builds that they did not need.

## 1. Waves have to be data, not code

The first version is always a `Timer` and a `spawn_enemy()` that gets an `if` added to
it every session. By hour ten it is a wall of conditionals nobody can tune.

The fix is not clever, it is just early: waves are a resource you edit, not a function
you extend.

```gdscript
class_name Wave
extends Resource

@export var enemy: PackedScene
@export var starts_at: float = 0.0     ## seconds into the run
@export var ends_at: float = 60.0
@export var per_second: float = 2.0
@export var hp_mult: float = 1.0
```

```gdscript
func _process(delta: float) -> void:
    _t += delta
    for wave in waves:
        if _t < wave.starts_at or _t > wave.ends_at:
            continue
        _budget[wave] = _budget.get(wave, 0.0) + wave.per_second * delta
        while _budget[wave] >= 1.0:
            _budget[wave] -= 1.0
            _spawn(wave)
```

The accumulator matters more than it looks. Spawning on a `Timer` ties your difficulty
curve to frame rate and to timer granularity; accumulating a float budget lets you say
"2.4 enemies per second" and actually get it.

Once waves are resources, balancing stops being programming. That is the whole point —
you will re-tune this a hundred times before release.

## 2. Enemy count is the thing that breaks first

The genre's entire fantasy is *too many of them*. That means the first wall you hit is
not AI, it is allocation: three hundred enemies spawning and dying every few seconds.

Two decisions carry almost all of it:

- **Pool the enemies and the bullets.** Not because allocation is slow on average, but
  because the spike lands in one frame, exactly when the screen is busiest. I wrote the
  honest version of this trade-off in
  [object pooling vs instantiate](https://saltmire.github.io/godot-4-object-pooling-vs-instantiate.html) —
  including when pooling is a waste of your time.
- **Do not give each enemy a `_process`.** Three hundred script callbacks per frame is
  real cost for behaviour that is "walk toward the player". Move them from one manager
  loop over a packed array of positions, and let the node be a dumb sprite.

## 3. The upgrade draft is the actual game

Movement is the verb, but the reason people replay is the level-up screen. Three cards,
one choice, a build that compounds. That system needs to be data from the first day,
because you are going to write eighty of these.

```gdscript
class_name Upgrade
extends Resource

@export var id: StringName
@export var title: String
@export var max_stacks: int = 5
@export var weight: float = 1.0
@export var requires: Array[StringName] = []   ## unlocks that must exist first
```

```gdscript
func draft(count: int = 3) -> Array[Upgrade]:
    var pool := all.filter(func(u): return _eligible(u))
    var picks: Array[Upgrade] = []
    var total := 0.0
    for u in pool:
        total += u.weight
    while picks.size() < count and not pool.is_empty():
        var roll := randf() * total
        for u in pool:
            roll -= u.weight
            if roll <= 0.0:
                picks.append(u)
                total -= u.weight
                pool.erase(u)
                break
    return picks
```

Weighted, filtered by what the player already owns, drawn without replacement. That is
the whole engine. Everything else is content you can write on a bad day.

## 4. Damage has to be honest

With hundreds of overlapping bodies, the bugs stop being visual and start being unfair:
a hit that lands twice in one swing, a hit that fires a damage number for a target that
was invincible, knockback that reads as a teleport.

The three rules that fix nearly all of it:

- **One hit per swing.** A lingering hitbox must not drain a target every frame.
- **Invincibility frames on the receiver**, not the attacker.
- **The hit event fires only when damage was actually taken.** If the target was in
  i-frames, no number, no spark, no sound. Nothing is more confusing than feedback for
  a hit that did not happen.

If you are wiring this from scratch, the layer/mask half of it is covered in
[hitbox and hurtbox the easy way](https://saltmire.github.io/godot-4-hitbox-hurtbox.html).

## 5. Meta progression decides whether run two happens

This is the one everybody bolts on last. It is also the one that turns a demo into a
game, because it is the reason to press "again" after dying at minute nine.

It does not need to be big. Currency earned per run, a handful of permanent unlocks,
and a save file that survives a crash mid-run. What it does need is to exist *before*
you tune difficulty, because permanent upgrades change every balance number you already
set.

## What you can skip

- **Pathfinding.** Enemies walk at the player. A steering vector and a cheap separation
  push between neighbours looks better than A\* here, and costs a fraction.
- **Per-enemy AI scripts.** One state and a speed value covers ninety percent of the
  roster. Save the scripting for the three enemies that actually do something.

## Build it or start from one

If you want to learn the genre, build it. All five systems above are honest work and
none of them is beyond a solo dev — that is why the write-up exists.

If you want to ship, the argument for starting from a template is that the five systems
above are the ones you would spend a month getting wrong first. The
[Survivors Template](https://saltmire.itch.io/survivors-template-godot) is the
data-driven version of exactly this — waves, draft, pooling and meta progression already
wired, with the full source and a playable web demo so you can judge the feel before
paying anything.

The rest of the tools I use for the combat and feel layer are on the
[tools page](https://saltmire.github.io/tools.html), most of them free and MIT.
