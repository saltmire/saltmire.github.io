---
title: JSON vs ConfigFile vs Resource in Godot 4 — which save format and when
description: A practical Godot 4 comparison of the three built-in ways to save a game — JSON, ConfigFile and custom Resources — covering type loss, Vector2 round-trips, the security warning on .tres saves, modding and schema changes, with a rule for picking one.
slug: godot-4-json-vs-configfile-vs-resource-save
date: 2026-10-17
product_name: Saltmire Save
product_url: https://saltmire.itch.io/saltmire-save
---

Godot 4 gives you three sanctioned ways to write a save file, and the docs describe each
one without ever telling you which to pick. So you pick the first one you read about,
ship it, and discover the trade-off six months later when a player's `Vector2` comes back
as a `Dictionary` or an old save crashes the new build. Here's what each format actually
costs.

## JSON: portable, readable, type-lossy

`FileAccess` plus `JSON` is the path most tutorials take, because it's the one that
looks like saving in every other language.

```gdscript
func save_game(data: Dictionary) -> void:
	var f := FileAccess.open("user://save.json", FileAccess.WRITE)
	f.store_string(JSON.stringify(data, "\t"))

func load_game() -> Dictionary:
	if not FileAccess.file_exists("user://save.json"):
		return {}
	var f := FileAccess.open("user://save.json", FileAccess.READ)
	var parsed = JSON.parse_string(f.get_as_text())
	return parsed if parsed is Dictionary else {}
```

The catch is that JSON has no idea what a Godot type is. It knows objects, arrays,
strings, numbers, booleans and null — that's the whole list. Three consequences bite in
practice:

- **Numbers come back as floats.** Save `level = 3`, load `3.0`. Anything you feed to an
  array index or a `match` on an int needs an explicit `int()` on the way out.
- **Dictionary keys become strings.** `{1: "sword"}` saves and loads as `{"1": "sword"}`.
  Inventory slots keyed by int are the usual victim.
- **Vector2, Color and friends don't survive.** You convert them by hand going in and
  coming out, every field, forever.

What you get in exchange is real: the file is plain text any tool can read, nothing in it
can execute, and you can parse it outside Godot — a web leaderboard, a Python script, a
save editor you write in an afternoon.

## ConfigFile: Variants that round-trip, in an INI file

`ConfigFile` stores sections and keys, and it keeps Godot's own types.

```gdscript
func save_game() -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("player", "position", Vector2(120, 48))
	cfg.set_value("player", "hp", 3)
	cfg.set_value("world", "unlocked", ["cave", "ridge"])
	cfg.save("user://save.cfg")

func load_game() -> void:
	var cfg := ConfigFile.new()
	if cfg.load("user://save.cfg") != OK:
		return
	var pos: Vector2 = cfg.get_value("player", "position", Vector2.ZERO)
	var hp: int = cfg.get_value("player", "hp", 3)
```

`Vector2` goes in and `Vector2` comes out. `3` stays an `int`. Arrays and Dictionaries of
Variants work too, and `get_value()` takes a default as its third argument — which quietly
solves the "player has an old save without this key" problem that forces try/except
gymnastics in JSON.

The limits: it stores Variants, not objects, so a custom class instance isn't going in.
It's flat by nature — two levels, section and key — so deeply nested state gets encoded as
one big Dictionary value and you've lost the readability you came for. And the format is
Godot's own, so nothing outside the engine parses it for free.

## Resource: typed, autocompleted, and the one with a security warning

A custom `Resource` turns your save into a class with real fields.

```gdscript
class_name SaveData extends Resource

@export var hp: int = 3
@export var position: Vector2 = Vector2.ZERO
@export var unlocked: Array[String] = []
```

```gdscript
func save_game(data: SaveData) -> void:
	ResourceSaver.save(data, "user://save.tres")

func load_game() -> SaveData:
	if not ResourceLoader.exists("user://save.tres"):
		return SaveData.new()
	return load("user://save.tres") as SaveData
```

Typos become editor errors instead of runtime nils, and you get autocomplete on your own
save. It is by far the nicest to write.

Two things to know before you ship it. First, **resource files can reference scripts, and
loading one runs them** — the Godot docs say outright not to load resources from untrusted
sources. A save file in `user://` is a file the player (or anything else on their machine)
can swap. If your game ever accepts a save from elsewhere — cloud sync, a Discord
"try my seed", a modding scene — that's a code-execution path, not just a cheating one.
Second, the file is tied to your script: rename the class, move the file, or drop an
`@export` and old saves stop loading cleanly.

## The comparison

| | JSON | ConfigFile | Resource (.tres) |
|---|---|---|---|
| Keeps `int` vs `float` | no | yes | yes |
| `Vector2` / `Color` round-trip | manual | yes | yes |
| Dictionary int keys | become strings | yes | yes |
| Typed fields + autocomplete | no | no | yes |
| Readable / editable by players | yes | yes | yes (and riskier) |
| Parseable outside Godot | yes | no | no |
| Missing key has a default | hand-rolled | built in | class default |
| Safe to load untrusted files | yes | yes | **no** |
| Survives renaming your classes | yes | yes | no |
| Built-in password encryption | via `FileAccess` | `save_encrypted_pass` | no |

One honest note on that last row: the key ships inside your game binary, so encryption
here stops casual editing, not a determined player.

## The rule

**Shipping a single-player game and you want the least future pain?** ConfigFile. It
round-trips Godot's types, defaults are built in, and nothing in it can run.

**Anything outside Godot ever reads the save** — a server, a stats page, a tool? JSON, and
pay the type-casting tax deliberately.

**Prototype or jam, all internal, speed is everything?** Resource. Just know you'll want
to move off it before you accept a save file you didn't write.

Whichever you pick, the format is the easy half. The half that shows up later is
versioning old saves into a new schema, not corrupting the file when the game is killed
mid-write, and keeping a backup to fall back on. Saltmire Save is the paid tool I built
after writing that layer one time too many: one-line save and load, plus schema migration,
backup recovery, gzip compression and encryption — MIT licensed, so you can read exactly
how it handles each of these.
