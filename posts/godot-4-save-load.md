---
title: How to save and load your game in Godot 4 (the honest way)
description: A complete, working save/load system in Godot 4 using FileAccess and JSON — plus the four production problems nobody warns you about.
slug: godot-4-save-load
date: 2026-07-08
product_name: Saltmire Save Lite
product_url: https://saltmire.itch.io/saltmire-save-lite
---

Every game needs to save state, and Godot 4 gives you everything you need in the
standard library. Here is a real, working system you can paste into a project
today — followed by the parts that quietly break in production.

## The minimal version

Godot's `FileAccess` writes bytes; `JSON` turns a `Dictionary` into a string and
back. Put the two together and you have save/load:

```gdscript
const SAVE_PATH := "user://savegame.json"

func save_game(data: Dictionary) -> void:
    var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
    f.store_string(JSON.stringify(data))
    f.close()

func load_game() -> Dictionary:
    if not FileAccess.file_exists(SAVE_PATH):
        return {}
    var f := FileAccess.open(SAVE_PATH, FileAccess.READ)
    var text := f.get_as_text()
    f.close()
    var parsed = JSON.parse_string(text)
    return parsed if typeof(parsed) == TYPE_DICTIONARY else {}
```

Call `save_game({"hp": 80, "level": 3})` and later `var d = load_game()`. That is
genuinely all you need for a jam game.

## Why `user://` and not `res://`

`res://` is your project — it is **read-only** in an exported game. Always save to
`user://`, which maps to a real per-user folder on desktop and to IndexedDB on the
web export. Same API either way, so your code does not change per platform.

## Multiple save slots

Do not hardcode one path. Key the filename by a slot name so you can build a
load-game menu:

```gdscript
func slot_path(slot: String) -> String:
    return "user://saves/%s.json" % slot

func save_to(slot: String, data: Dictionary) -> void:
    DirAccess.make_dir_recursive_absolute("user://saves")
    var f := FileAccess.open(slot_path(slot), FileAccess.WRITE)
    f.store_string(JSON.stringify(data))
    f.close()
```

To list existing slots for a menu, walk the directory with `DirAccess`.

## The four things that bite later

The snippet above works — until real players use it. These are the problems that
turn a two-line save system into a two-week refactor:

1. **Corruption.** A crash or power-off mid-write leaves a half-written file.
   `JSON.parse_string` returns `null` and the player loses everything. The fix is
   to write to a temp file, then rename over the real one, and keep a rotating
   backup to restore from.
2. **Save editing.** A plain JSON file in `user://` is trivial to open and edit —
   players will change their gold to 9999. If that matters, you need to encrypt
   the file (`FileAccess.open_encrypted_with_pass`).
3. **Schema changes.** You ship an update that renames `coins` to `gold`. Every
   existing save still has `coins`. Without a migration step, old saves crash or
   silently lose data.
4. **Save size.** A big world save is megabytes of JSON. gzip typically cuts that
   by ~90%, but only helps if you wire compression in from the start.

None of these are hard individually. The problem is that they all show up *after*
launch, one at a time, in bug reports.

## If you just want it handled

You can build all four yourself — or drop in a tool that already has them, with a
headless self-test that proves each one with a real number. That is exactly what
Saltmire Save Lite (free) and Saltmire Save (the full version) are for: the same
one-line `Save.write` / `Save.read` API, with encryption, backups, migration and
compression when you need them.
