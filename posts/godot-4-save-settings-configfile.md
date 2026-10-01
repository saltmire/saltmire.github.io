---
title: How to save game settings (volume, fullscreen, keybinds) in Godot 4 with ConfigFile
description: A practical Godot 4 tutorial for an options menu that remembers itself — a Settings autoload backed by ConfigFile, audio bus volume, fullscreen and vsync, and keyboard rebinds that survive a restart.
slug: godot-4-save-settings-configfile
date: 2026-10-01
product_name: Saltmire Save Lite
product_url: https://saltmire.itch.io/saltmire-save-lite
---

Every player opens the options menu, turns the music down, and expects it to *stay* down
next time. In Godot 4 the right tool for that is not your save system and not JSON — it's
`ConfigFile`, a tiny INI-style file that Godot reads and writes in one call.

This tutorial builds a `Settings` autoload that stores volume, fullscreen, vsync and
keyboard rebinds in `user://settings.cfg` and re-applies them every time the game starts.

## Why ConfigFile for settings

- It's human-readable (`[audio]` / `master=0.8`), so you can debug it by opening the file.
- `get_value(section, key, default)` gives you a fallback for free — a missing key never crashes.
- Settings are **per machine**, not per save slot. Keeping them out of your game save means
  deleting a slot never resets the player's volume.

## Step 1: the Settings autoload

Create `settings.gd` and register it in **Project → Project Settings → Globals → Autoload**
with the name `Settings`.

```gdscript
extends Node

const PATH := "user://settings.cfg"

var config := ConfigFile.new()

func _ready() -> void:
	var err := config.load(PATH)
	if err != OK and err != ERR_FILE_NOT_FOUND:
		push_warning("Settings: could not read %s (error %d), using defaults" % [PATH, err])
	apply_all()

func get_setting(section: String, key: String, default_value: Variant) -> Variant:
	return config.get_value(section, key, default_value)

func set_setting(section: String, key: String, value: Variant) -> void:
	config.set_value(section, key, value)

func save() -> void:
	var err := config.save(PATH)
	if err != OK:
		push_error("Settings: save failed (error %d)" % err)

func apply_all() -> void:
	apply_volume("Master")
	apply_volume("Music")
	apply_volume("SFX")
	apply_display()
	apply_keybinds()
```

`ERR_FILE_NOT_FOUND` on the very first launch is normal — there's no file yet, so every
`get_value` falls back to its default.

## Step 2: audio volume per bus

Store volume as a **linear 0.0–1.0** value (what a slider gives you) and convert to
decibels only when applying. Make sure the buses `Music` and `SFX` exist in the Audio tab,
or skip them.

```gdscript
func apply_volume(bus_name: String) -> void:
	var idx := AudioServer.get_bus_index(bus_name)
	if idx == -1:
		return
	var linear: float = get_setting("audio", bus_name.to_lower(), 1.0)
	AudioServer.set_bus_volume_db(idx, linear_to_db(linear))
	AudioServer.set_bus_mute(idx, linear <= 0.001)
```

The mute line matters: `linear_to_db(0.0)` is `-inf`, and muting the bus at zero is cleaner
than relying on it.

## Step 3: fullscreen and vsync

```gdscript
func apply_display() -> void:
	var fullscreen: bool = get_setting("display", "fullscreen", false)
	DisplayServer.window_set_mode(
		DisplayServer.WINDOW_MODE_FULLSCREEN if fullscreen
		else DisplayServer.WINDOW_MODE_WINDOWED)

	var vsync: bool = get_setting("display", "vsync", true)
	DisplayServer.window_set_vsync_mode(
		DisplayServer.VSYNC_ENABLED if vsync else DisplayServer.VSYNC_DISABLED)
```

On the web export, fullscreen requires a user gesture, so call this from a button press
rather than only at startup.

## Step 4: keyboard rebinds that persist

Storing whole `InputEvent` objects works but makes the file noisy. For keyboard bindings,
the physical keycode (an `int`) is enough and survives keyboard layout changes.

```gdscript
const REBINDABLE := ["move_left", "move_right", "jump", "attack"]

func rebind(action: String, event: InputEventKey) -> void:
	# Replace only the keyboard event; keep gamepad bindings intact.
	for old in InputMap.action_get_events(action):
		if old is InputEventKey:
			InputMap.action_erase_event(action, old)
	InputMap.action_add_event(action, event)
	set_setting("keybinds", action, event.physical_keycode)

func apply_keybinds() -> void:
	for action in REBINDABLE:
		var code: int = get_setting("keybinds", action, 0)
		if code == 0:
			continue  # never rebound — keep the Input Map default
		var ev := InputEventKey.new()
		ev.physical_keycode = code
		for old in InputMap.action_get_events(action):
			if old is InputEventKey:
				InputMap.action_erase_event(action, old)
		InputMap.action_add_event(action, ev)
```

To capture the new key, put a "press any key" state in your rebind button and grab the
next `InputEventKey` in `_unhandled_input`, then call `Settings.rebind(action, event)`.

## Step 5: wire the options menu

```gdscript
extends Control

@onready var music_slider: HSlider = %MusicSlider
@onready var fullscreen_check: CheckButton = %FullscreenCheck

func _ready() -> void:
	music_slider.value = Settings.get_setting("audio", "music", 1.0)
	fullscreen_check.button_pressed = Settings.get_setting("display", "fullscreen", false)

	music_slider.value_changed.connect(func(v: float) -> void:
		Settings.set_setting("audio", "music", v)
		Settings.apply_volume("Music"))
	music_slider.drag_ended.connect(func(_changed: bool) -> void:
		Settings.save())

	fullscreen_check.toggled.connect(func(on: bool) -> void:
		Settings.set_setting("display", "fullscreen", on)
		Settings.apply_display()
		Settings.save())
```

Set the slider's range to `0`–`1` with a step of `0.05`. Apply on every `value_changed`
so the player hears the change live, but only write to disk on `drag_ended` — no need to
hit the file system 60 times a second.

## Common mistakes

- **Saving to `res://`.** It's read-only in exported games. Always use `user://`.
- **Applying settings in the menu scene only.** If the menu isn't loaded, nothing applies.
  That's why `apply_all()` runs in the autoload's `_ready()`.
- **Storing decibels.** Sliders feel wrong in dB; store linear, convert on apply.
- **Mixing settings into the save slot.** One file per machine for settings, one per slot
  for progress.

## Wrapping up

`ConfigFile` covers the options menu. Your actual game progress — player stats, inventory,
unlocked levels — is a different job, and that's the part where writing your own
serialization gets tedious. If you'd rather save and load that state in a single call,
Saltmire Save Lite is a free, MIT-licensed add-on that does exactly that.
