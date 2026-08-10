---
title: What I learned building a save-slot menu in Godot 4
description: Lessons from building a multi-slot save menu in Godot 4 — thumbnail screenshots, corrupt-slot handling, the "new game" vs "continue" trap, and why a single save file always turns into three slots eventually.
slug: godot-4-save-slot-menu
date: 2026-08-10
product_name: Saltmire Save
product_url: https://saltmire.itch.io/saltmire-save
---

I built save/load for a project three separate times before I admitted the real work was
never the file I/O. It was the menu. Here is what actually cost time, in the order it bit me.

## Lesson 1: "one save file" always becomes "N save slots"

Every prototype starts with `user://save.dat` and a single Continue button. Then a
playtester asks "can I have two characters going at once?" and the whole save layer has
to grow a slot number it was never designed to carry.

Design the path with a slot from day one, even if you ship with one slot:

```gdscript
func slot_path(slot: int) -> String:
	return "user://save_slot_%d.json" % slot
```

Retrofitting this later means migrating existing players' saves, which is lesson 4.

## Lesson 2: the menu needs data the save file doesn't have yet

A save-slot screen wants to show a thumbnail, a play-time, a location name, and a
timestamp — none of which live naturally inside your gameplay save data. I kept trying to
derive them from the save file at load time, which meant loading every slot just to draw
the menu. Slow, and it loads slots the player never picks.

The fix is a tiny separate metadata blob written alongside the save, cheap to read for
every slot up front:

```gdscript
func write_meta(slot: int, area_name: String, play_seconds: float) -> void:
	var meta := {
		"area": area_name,
		"play_seconds": play_seconds,
		"saved_at": Time.get_datetime_string_from_system(),
		"thumb": "user://save_slot_%d.png" % slot,
	}
	var f := FileAccess.open("user://save_slot_%d.meta.json" % slot, FileAccess.WRITE)
	f.store_string(JSON.stringify(meta))
```

The menu reads N small `.meta.json` files, not N full save files. Loading the actual slot
only happens once the player commits to it.

## Lesson 3: the thumbnail is a viewport capture, and timing matters

Grabbing a screenshot for the slot thumbnail is one call, but calling it at the wrong
moment gives you a black square or a half-drawn frame:

```gdscript
func save_thumbnail(slot: int) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.resize(320, 180)
	img.save_png("user://save_slot_%d.png" % slot)
```

Awaiting `frame_post_draw` instead of just calling it inline was the difference between a
usable thumbnail and a black one — the viewport texture isn't guaranteed populated on the
same frame you request the save.

## Lesson 4: "new game" and "continue" are the same button, and that's the bug

I originally wired an empty slot to "New Game" and a filled slot to "Continue" as two
different UI states. That is correct until a slot's save file gets corrupted — then the
slot has data but nothing loads, and the player is stuck on a menu that offers no way
forward. Every slot needs a fallback path from "load failed" back to "start over in this
slot," not just a happy path:

```gdscript
func open_slot(slot: int) -> void:
	var result := SaveGame.load_slot(slot)
	if result.ok:
		start_game(result.data)
	elif FileAccess.file_exists(slot_path(slot)):
		show_corrupt_slot_dialog(slot)   # offer: retry, restore backup, or overwrite
	else:
		start_new_game(slot)
```

This is the one lesson I'd tell past-me to learn first — a corrupt slot isn't an edge
case, it's a guarantee over a long enough playtest, and the menu is the only place a
player can recover from it.

## Lesson 5: deleting a slot needs a confirm, and needs to actually delete the metadata too

Obvious in hindsight, but I shipped a build where "delete slot" removed the save file and
left the `.meta.json` and `.png` behind — so the empty slot still rendered a thumbnail and
a play-time from the deleted run. Delete is three files, not one, or the slot lies to the
player.

## What I'd do differently starting over

Build the slot number and the metadata sidecar file on day one, even for a single-slot
game — it costs nothing early and it is the exact thing that's expensive to retrofit.
Treat "load failed" as a menu state you design for, not an exception you catch. And test
delete by actually looking at the file list after, not just the menu.

The mechanics of reading and writing JSON to `user://` are the easy 20% of "add saving" to
a game. The slot menu, the corrupt-file recovery, and the thumbnail timing are the other
80%, and none of it is specific to any one game — which is exactly the kind of thing worth
not re-solving from scratch every project.
