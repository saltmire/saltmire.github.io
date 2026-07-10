---
title: "Fixing Godot 4 save-file load errors: JSON parse error, null instance, and missing files"
description: The three save/load errors that break Godot 4 games — JSON parse error at end of file, attempt to call on a null instance, and file not found — with the cause and the exact fix for each.
slug: godot-4-save-file-load-errors
date: 2026-07-10
product_name: Saltmire Save
product_url: https://saltmire.itch.io/saltmire-save
---

You shipped a save system, it worked on your machine, and now the console is red on
load. Save/load bugs are nasty because they only show up *after* a write already
happened — the bad data is already on disk. Here are the three errors that break
Godot 4 saves most often, why each one happens, and the exact fix.

## 1. `JSON Parse Error: ... at line N`

**Symptom.** On load you get something like:

```
JSON Parse Error: Unexpected end of stream at line 1
```

or a parse error pointing at a spot in the middle of your file.

**Cause.** The file was written partially. This almost always means the game
crashed (or was force-quit) *during* the write, or two systems wrote to the same
file at once. `FileAccess` flushes on `close()`; if you never reach `close()`, you
get a truncated, unparseable file.

**Fix.** Never write in place. Write to a temp file, then rename it over the real
one — rename is atomic on every desktop OS, so the save is either the old file or
the complete new one, never a half of each:

```gdscript
func save_state(data: Dictionary, path := "user://save.json") -> void:
    var tmp := path + ".tmp"
    var f := FileAccess.open(tmp, FileAccess.WRITE)
    if f == null:
        push_error("Save failed to open %s: %d" % [tmp, FileAccess.get_open_error()])
        return
    f.store_string(JSON.stringify(data))
    f.close()  # flush BEFORE the rename
    DirAccess.rename_absolute(ProjectSettings.globalize_path(tmp),
                              ProjectSettings.globalize_path(path))
```

And always guard the read instead of trusting `JSON.parse_string`:

```gdscript
func load_state(path := "user://save.json") -> Dictionary:
    if not FileAccess.file_exists(path):
        return {}
    var text := FileAccess.get_file_as_string(path)
    var parsed = JSON.parse_string(text)
    if parsed == null or typeof(parsed) != TYPE_DICTIONARY:
        push_warning("Save at %s is corrupt — falling back to empty." % path)
        return {}
    return parsed
```

## 2. `Invalid call ... Attempt to call ... on a null instance`

**Symptom.**

```
Invalid call. Nonexistent function 'get' in base 'Nil'.
```

right after you read the save back.

**Cause.** `JSON.parse_string` returns `null` on failure, and you used the result
without checking. It also *cannot* return your original types — a `Vector2` you
stored becomes a plain array or `null`, a custom object becomes a Dictionary. So
`saved.player_pos.x` blows up because `player_pos` is not a `Vector2` anymore.

**Fix.** Serialize non-JSON types explicitly on the way out, and rebuild them on the
way in. Don't assume the shape survived:

```gdscript
# on save
data["player_pos"] = {"x": player.position.x, "y": player.position.y}

# on load
var d: Dictionary = load_state()
if d.has("player_pos"):
    var p = d["player_pos"]
    player.position = Vector2(p.get("x", 0.0), p.get("y", 0.0))
```

Every read from the loaded dictionary should use `.get(key, default)` so a missing
key gives a sane value instead of a `Nil`.

## 3. `Error opening file` / values silently wrong after an update

**Symptom.** Either the file just isn't there on a fresh install, or a returning
player loads an old save and half their state is missing after you added fields.

**Cause.** Two separate issues wearing the same coat: (a) you read before any save
exists, and (b) the save's *schema* changed between versions and old files don't
have the new keys.

**Fix.** Version your saves and migrate forward. Stamp a version number on write,
and run migrations on read so an old file becomes a valid current one:

```gdscript
const SAVE_VERSION := 3

func migrate(d: Dictionary) -> Dictionary:
    var v := int(d.get("version", 1))
    if v < 2:
        d["settings"] = d.get("settings", {"volume": 1.0})  # added in v2
    if v < 3:
        d["playtime"] = d.get("playtime", 0.0)              # added in v3
    d["version"] = SAVE_VERSION
    return d
```

Now old saves keep loading instead of erroring, and new fields get safe defaults.

## The pattern behind all three

Every one of these bugs is the same root cause: treating the disk as trustworthy.
It isn't. A robust save layer writes atomically, validates on read, defaults every
missing key, and migrates old schemas — none of which is hard, but all of which is
easy to forget until a player loses a save. If you'd rather not re-derive the atomic
write, corruption guard, backup fallback, and schema migration in every project,
that's exactly the boring, tested wiring Saltmire Save is.
