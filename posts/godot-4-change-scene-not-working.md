---
title: "Godot 4 change_scene_to_file not working? 4 causes and fixes"
description: get_tree().change_scene_to_file() fails silently, throws "Can't change this state while flushing queries", crashes with a null get_tree(), or fires twice. Here are the 4 real causes in Godot 4 — code running after the scene is gone, physics callbacks, broken paths in exports, and double triggers — each with the exact fix.
slug: godot-4-change-scene-not-working
date: 2026-09-27
product_name: Saltmire Transitions
product_url: https://saltmire.itch.io/saltmire-transitions-scene-transition-kit-for-godot-4
---

Changing scenes in Godot 4 looks like a one-liner: `get_tree().change_scene_to_file("res://level_2.tscn")`.
Then the door trigger throws an error, the game crashes one line later, or the build
you exported loads a black screen. The call itself is almost never the bug — what
happens *around* it is. Here are the four causes, ordered by how often they show up.

## 1. Code after the call runs on a scene that's already gone

**Symptom.** The scene changes, but you get
`Cannot call method 'get_first_node_in_group' on a null value` (or any
`get_tree()`-based call failing) on the line right after `change_scene_to_file()`.

**Cause.** Since Godot 4.2, the outgoing scene is removed from the tree
*immediately* when you call `change_scene_to_file()`. From that point until the end
of the frame, `get_tree()` on that scene returns `null` and
`get_tree().current_scene` is `null` too — the new scene isn't added until the end
of the frame. So anything you do after the call is running on a node that's no
longer in the tree.

```gdscript
# broken — get_tree() is null on the second line
func _on_exit_reached() -> void:
    get_tree().change_scene_to_file("res://levels/level_2.tscn")
    get_tree().current_scene.spawn_player()  # null
```

**Fix.** Make the scene change the *last* thing the old scene does. Anything the new
scene needs goes into an autoload beforehand, and the new scene reads it in its own
`_ready()`:

```gdscript
# old scene
func _on_exit_reached() -> void:
    GameState.spawn_point = "north_door"   # autoload survives the change
    get_tree().change_scene_to_file("res://levels/level_2.tscn")

# new scene (level_2.gd)
func _ready() -> void:
    var marker := get_node("Spawns/" + GameState.spawn_point) as Marker2D
    $Player.global_position = marker.global_position
```

## 2. "Can't change this state while flushing queries"

**Symptom.** You change scene from a `body_entered` / `area_entered` signal (a door,
a level exit, a death pit) and the output fills with
`Can't change this state while flushing queries. Use call_deferred() or set_deferred() to change monitoring state instead.`

**Cause.** Those signals fire *during* the physics step, while the physics server is
still processing collisions. Changing the scene removes every `Area2D` and
`CollisionShape2D` in it right then — in the middle of the step that's iterating
over them.

**Fix.** Defer the call so it runs after the physics step finishes:

```gdscript
func _on_body_entered(body: Node2D) -> void:
    if body.is_in_group("player"):
        get_tree().change_scene_to_file.call_deferred("res://levels/level_2.tscn")
```

The same rule applies to anything else that adds or frees collision nodes from inside
a physics callback — defer it.

## 3. The path breaks after a rename — or only in the exported build

**Symptom.** It worked yesterday, now nothing happens. Or it works perfectly in the
editor but the exported game shows a black screen or stays on the same scene.

**Cause.** `change_scene_to_file()` doesn't throw — it returns an `Error`, and most
code ignores it. Two common reasons it fails:

- You moved or renamed the `.tscn` in the FileSystem dock. The editor updates
  references inside scenes, but **not** string literals in your scripts.
- Case mismatch: `res://Levels/Level_2.tscn` vs `res://levels/level_2.tscn`. Windows
  and macOS don't care in the editor; the exported `.pck` does.

**Fix.** First, stop ignoring the return value:

```gdscript
var err := get_tree().change_scene_to_file(path)
if err != OK:
    push_error("Scene change to %s failed: %s" % [path, error_string(err)])
```

Then remove the fragile string entirely. Export a `PackedScene` and drag the file into
the Inspector — Godot tracks it by UID, so renames and moves keep working:

```gdscript
@export var next_scene: PackedScene

func go_next() -> void:
    get_tree().change_scene_to_packed.call_deferred(next_scene)
```

## 4. The change fires twice

**Symptom.** Your fade plays twice, a level gets skipped, or you get a second error
right after the first scene change.

**Cause.** The player's body often overlaps a trigger with more than one shape, or
re-enters it on the same frame, so `body_entered` fires more than once. Each call
queues another scene change — and if you have a fade tween in front of it, you now
have two tweens racing each other.

**Fix.** Guard it with a flag and switch the trigger off on the first hit:

```gdscript
var _leaving := false

func _on_body_entered(body: Node2D) -> void:
    if _leaving or not body.is_in_group("player"):
        return
    _leaving = true
    set_deferred("monitoring", false)
    get_tree().change_scene_to_packed.call_deferred(next_scene)
```

## What all four have in common

A scene change is a destructive operation on the whole tree: it frees every node,
including the one that asked for it. Treat it like `queue_free()` on yourself —
do it last, do it deferred when physics is involved, point it at a tracked
resource instead of a string, and make sure it only happens once.

Once that's solid, the next thing most games want is a transition that hides the
cut — and wiring a fade, a loading step and the deferred change together is exactly
where these four bugs love to come back. Saltmire Transitions packages that part
into a single call, with the fades, wipes and the safe scene swap already handled,
and it's free.
