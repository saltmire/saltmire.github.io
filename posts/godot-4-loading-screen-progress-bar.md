---
title: How to add a loading screen with a progress bar in Godot 4
description: A practical Godot 4 tutorial for threaded scene loading — a CanvasLayer loading screen, a ProgressBar wired to ResourceLoader.load_threaded_get_status, and tips for minimum display time and a fade-out transition.
slug: godot-4-loading-screen-progress-bar
date: 2026-09-20
product_name: Saltmire Transitions
product_url: https://saltmire.itch.io/saltmire-transitions-scene-transition-kit-for-godot-4
---

The default `get_tree().change_scene_to_file()` works fine for small scenes — but once
your scenes grow (packed tilemaps, many enemies, heavy resources), the player will see a
frozen frame before anything appears. The fix is threaded loading with a real progress bar.

## How Godot 4 threaded loading works

Godot 4's `ResourceLoader` can load a scene in a background thread while your loading
screen stays interactive. There are three calls you need:

- `load_threaded_request(path)` — queue the load; call once.
- `load_threaded_get_status(path, progress_array)` — poll every frame; fills
  `progress_array[0]` with a 0.0–1.0 float.
- `load_threaded_get(path)` — grab the finished `PackedScene` when status is
  `THREAD_LOAD_LOADED`.

## Step 1: build the loading screen scene

Create a new scene with a `CanvasLayer` root (name it `LoadingScreen`) and add two
children: a `ColorRect` that fills the screen and a `ProgressBar`.

Set the `ProgressBar`:
- `Min Value`: 0, `Max Value`: 100
- Anchor it full-width near the bottom, or centered — your call.
- `Show Percentage`: on or off, both are fine.

Attach this script to `LoadingScreen`:

```gdscript
extends CanvasLayer

@export var next_scene_path: String = ""

var _progress := []

func _ready() -> void:
    if next_scene_path.is_empty():
        push_error("LoadingScreen: next_scene_path is not set.")
        return
    ResourceLoader.load_threaded_request(next_scene_path)

func _process(_delta: float) -> void:
    if next_scene_path.is_empty():
        return
    var status := ResourceLoader.load_threaded_get_status(next_scene_path, _progress)
    if not _progress.is_empty():
        $ProgressBar.value = _progress[0] * 100.0
    match status:
        ResourceLoader.THREAD_LOAD_LOADED:
            var scene: PackedScene = ResourceLoader.load_threaded_get(next_scene_path)
            get_tree().change_scene_to_packed(scene)
        ResourceLoader.THREAD_LOAD_FAILED:
            push_error("LoadingScreen: failed to load " + next_scene_path)
```

## Step 2: trigger it from any scene

Anywhere you would have called `change_scene_to_file("res://levels/level_2.tscn")`, do
this instead:

```gdscript
func _go_to_next_level() -> void:
    var loader: PackedScene = preload("res://ui/LoadingScreen.tscn")
    var screen := loader.instantiate()
    screen.next_scene_path = "res://levels/level_2.tscn"
    get_tree().root.add_child(screen)
```

The loading screen overlays the current scene, starts loading `level_2.tscn` in the
background, and swaps out once the load is done. The current scene never freezes.

## Step 3: enforce a minimum display time

For small scenes, loading finishes in milliseconds and the progress bar flashes past.
A minimum display time of 0.5–1 second feels less jarring:

```gdscript
const MIN_SHOW_TIME := 0.6

var _elapsed := 0.0
var _loaded_scene: PackedScene = null

func _process(delta: float) -> void:
    _elapsed += delta
    if next_scene_path.is_empty():
        return
    var status := ResourceLoader.load_threaded_get_status(next_scene_path, _progress)
    if not _progress.is_empty():
        $ProgressBar.value = _progress[0] * 100.0
    if status == ResourceLoader.THREAD_LOAD_LOADED and _loaded_scene == null:
        _loaded_scene = ResourceLoader.load_threaded_get(next_scene_path)
    if _loaded_scene != null and _elapsed >= MIN_SHOW_TIME:
        get_tree().change_scene_to_packed(_loaded_scene)
```

The scene is grabbed as soon as it is ready, but the transition waits until the minimum
time has passed. The progress bar still fills to 100% immediately — only the *switch* is
delayed.

## Step 4: add a fade-out before switching

`change_scene_to_packed` cuts instantly. To soften it, tween the `CanvasLayer` modulate
alpha to 0 before switching:

```gdscript
if _loaded_scene != null and _elapsed >= MIN_SHOW_TIME:
    var t := create_tween()
    t.tween_property(self, "modulate:a", 0.0, 0.3)
    await t.finished
    get_tree().change_scene_to_packed(_loaded_scene)
```

Keep the tween short (0.2–0.4 s). Anything longer kills pacing.

## Common gotcha: duplicate load requests

If you call `load_threaded_request` on a path that is already being loaded (for example,
a player hits a trigger twice), Godot returns `ERR_ALREADY_IN_USE`. Add a guard so it
does not spam errors:

```gdscript
func _ready() -> void:
    var err := ResourceLoader.load_threaded_request(next_scene_path)
    if err != OK and err != ERR_ALREADY_IN_USE:
        push_error("load_threaded_request failed: " + str(err))
```

`ERR_ALREADY_IN_USE` means the load is already queued — `load_threaded_get` will still
return the resource when it finishes, so no action needed.

## The finished loading screen

That is the whole setup: a `CanvasLayer` overlay, three `ResourceLoader` calls, an
optional minimum display time, and an optional fade-out. It works for any scene size.
If you want richer transitions on the way in or out — iris wipes, pixelate, dissolve,
or slides — Saltmire Transitions wraps those into a one-line call and handles the
scene-switch timing internally.
