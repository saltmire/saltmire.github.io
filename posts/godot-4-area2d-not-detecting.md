---
title: Godot 4 Area2D not detecting hits? 6 reasons area_entered isn't firing
description: Your Godot 4 Area2D won't detect collisions and area_entered never fires. Here are the 6 real causes — monitoring flags, layers vs masks, missing shapes, and the overlap-on-activate trap — each with the fix.
slug: godot-4-area2d-not-detecting
date: 2026-07-21
product_name: Saltmire Hitbox
product_url: https://saltmire.itch.io/saltmire-hitbox
---

You connected `area_entered`, you can see the two areas overlapping in the editor, and
nothing happens. This is the single most common Godot 4 combat bug, and it's almost
always one of these six things. Work down the list — they're ordered by how often
they're the culprit.

## 1. `monitoring` is off (or the wrong area is monitoring)

An `Area2D` only *detects* others when `monitoring = true`. And detection has a
direction: the scanner needs `monitoring`; the thing being found needs
`monitorable`. If both areas monitor each other you get double hits; if neither does,
you get silence.

```gdscript
# the attacker scans, doesn't need to be found:
hitbox.monitoring = true
hitbox.monitorable = false
# the target is found, doesn't scan:
hurtbox.monitoring = false
hurtbox.monitorable = true
```

## 2. Layers and masks don't line up (the classic)

`collision_layer` is *what you are*; `collision_mask` is *what you look for*. For A to
detect B, **A's mask must include B's layer.** Same number in both `layer` fields with
empty masks = they never see each other.

```gdscript
# hurtbox exists on layer 3:
hurtbox.collision_layer = 0
hurtbox.set_collision_layer_value(3, true)
hurtbox.collision_mask = 0
# hitbox looks for layer 3:
hitbox.collision_layer = 0
hitbox.set_collision_mask_value(3, true)
```

Check this in code, not just the inspector — a parent scene or tween can overwrite
layer bits at runtime and the panel won't show it.

## 3. There's no enabled `CollisionShape2D`

An `Area2D` with no shape (or a shape whose `disabled` is true, or whose `shape`
resource is null) has nothing to collide with. It fails silently — no error, no
warning.

```gdscript
var cs := hitbox.get_node("CollisionShape2D")
assert(cs.shape != null and not cs.disabled, "hitbox shape missing/disabled")
```

A frequent trap: calling `cs.disabled = true` to "turn off" an attack and forgetting
to flip it back before the next swing.

## 4. The signal is connected to the wrong node

`area_entered` fires on the area that's doing the monitoring. If you connected the
signal on the hurtbox but the hurtbox has `monitoring = false` (correct, per #1), the
callback never runs. Connect `area_entered` on the **monitoring** area, or use
`body_entered` if the other side is a `CharacterBody2D`/`StaticBody2D` rather than an
`Area2D`.

```gdscript
hitbox.area_entered.connect(_on_hit)   # hitbox monitors, so it emits
```

Mixing up `area_entered` (Area↔Area) and `body_entered` (Area↔Body) is its own silent
no-op — pick the one that matches what the other node actually is.

## 5. The hit started already overlapping (the melee trap)

`area_entered` only fires the frame two areas *begin* overlapping. If your hitbox
turns on while it's already sitting on top of the target — extremely common for a
melee swing that activates mid-contact — the signal never fires and the hit is lost.
Scan what's already inside when you activate:

```gdscript
func activate() -> void:
    monitoring = true
    for area in get_overlapping_areas():
        _on_hit(area)
```

Note `get_overlapping_areas()` is only accurate *after* at least one physics frame of
monitoring — if you enable and scan in the same frame, call
`await get_tree().physics_frame` first.

## 6. Physics is paused or the node is disabled

If the area's `process_mode` is `PROCESS_MODE_DISABLED`, or the tree is paused and the
node doesn't have `PROCESS_MODE_ALWAYS`, monitoring quietly stops. This bites during
hit-stop / slow-motion, when you drop `Engine.time_scale` or pause the tree for feel.

```gdscript
# keep the hitbox live through a pause used for hit-stop:
hitbox.process_mode = Node.PROCESS_MODE_ALWAYS
```

## The fast way to never hit this again

Every bug above comes from the same place: `Area2D` gives you the raw primitive and
makes you wire the rules — direction, layers, shapes, overlap-on-activate, pause
behavior — by hand, with no errors when you get it wrong. If you'd rather drop in two
nodes that already handle all six, that's exactly what Saltmire Hitbox is:
`Hitbox2D` / `Hurtbox2D` with zero layer setup, correct monitoring out of the box, and
the melee overlap case handled for you.
