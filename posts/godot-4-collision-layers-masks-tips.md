---
title: 7 Godot 4 collision layer and mask tips that save you an afternoon of debugging
description: Collision layers vs collision masks in Godot 4, explained with 7 practical tips — the one-line rule, naming layers, the 1-based vs bitmask trap, a constants script, one-way Area2D detection, raycast masks and TileSet physics layers.
slug: godot-4-collision-layers-masks-tips
date: 2026-10-03
product_name: Saltmire Hitbox Lite
product_url: https://saltmire.itch.io/saltmire-hitbox-lite
---

Collision layers and masks are the Godot 4 feature everybody "gets" in five minutes and
then fights for the rest of the project. The player walks through a wall, the enemy's
sword hits other enemies, a raycast sees nothing. Nine times out of ten the physics is
fine — the bits are wrong.

Here are seven tips that make the bits boring.

## 1. Layer is what you are, mask is what you look for

That is the whole rule. `collision_layer` says *which groups this object belongs to*.
`collision_mask` says *which groups this object scans for*. Write it down for your game
before you click a single checkbox:

| Node | Layer (what it is) | Mask (what it looks for) |
|---|---|---|
| Player body | player | world, enemy |
| Enemy body | enemy | world, player |
| Player sword (Area2D) | — | enemy_hurtbox |
| Enemy hurtbox (Area2D) | enemy_hurtbox | — |
| Walls / floor | world | — |

Notice the empty cells. Static walls don't need to look for anything — things look for
*them*. A hurtbox just needs to exist on a layer. Most layer bugs come from filling in
every cell "just in case".

## 2. Name your layers before you use them

Open **Project Settings → General → Layer Names → 2D Physics** and give layers 1–5 real
names: `world`, `player`, `enemy`, `player_hurtbox`, `enemy_hurtbox`. The inspector's
layer grid then shows those names on hover, and "why is the sword on layer 4" becomes
a question you can answer by reading.

You can read the names back in code, which is handy for a debug overlay:

```gdscript
func layer_name(n: int) -> String:
	return ProjectSettings.get_setting("layer_names/2d_physics/layer_%d" % n, "")
```

## 3. The inspector counts from 1, the raw property is a bitmask

This is the trap that costs the afternoon. In the inspector, layer 3 is the third box.
In code, `collision_layer` is a 32-bit **bitmask** — so this:

```gdscript
collision_layer = 3 # looks like "layer 3"
```

actually means *layers 1 and 2* (binary `011`). Layer 3 alone is `4`. Stop doing the
arithmetic in your head and use the 1-based helpers, which match the inspector:

```gdscript
collision_layer = 0
set_collision_layer_value(3, true)   # only layer 3
set_collision_mask_value(1, true)    # also scan layer 1
print(get_collision_mask_value(1))   # true
```

When something is off, print the mask in binary and read it right-to-left:

```gdscript
print(name, " layer=", String.num_int64(collision_layer, 2),
		" mask=", String.num_int64(collision_mask, 2))
```

## 4. Keep the numbers in one script

Once you set layers from code (spawned projectiles, a hitbox that changes team), magic
numbers spread fast. Put them in one place:

```gdscript
# res://physics_layers.gd
class_name PhysicsLayers

const WORLD := 1
const PLAYER := 2
const ENEMY := 3
const PLAYER_HURTBOX := 4
const ENEMY_HURTBOX := 5
```

```gdscript
# a bullet fired by the player
func _ready() -> void:
	collision_layer = 0
	collision_mask = 0
	set_collision_mask_value(PhysicsLayers.WORLD, true)
	set_collision_mask_value(PhysicsLayers.ENEMY_HURTBOX, true)
```

Keep these numbers in sync with the names from tip 2 and you never have to open the
project settings to remember what `5` meant.

## 5. Area2D detection is one-way — think from the detector's side

For an `Area2D` to report something in `area_entered` or `body_entered`, **the Area2D's
mask must include the other object's layer**. The other side's mask is irrelevant for
that signal. So for a sword hitting a hurtbox:

- the **sword** (the one listening) masks `enemy_hurtbox`,
- the **hurtbox** sits on layer `enemy_hurtbox` and keeps `monitorable = true`.

Listening from the hurtbox side instead works too — just mirror it. Pick one side.
Masking both ways *and* applying damage in both signal handlers is how one slash ends
up dealing damage twice.

Moving bodies follow the same idea: `move_and_slide()` only stops against objects whose
layer is in the **moving body's** mask. If the player walks through a wall, check the
player's mask for `world`, not the wall.

## 6. Raycasts and ShapeCasts have their own mask (and skip areas)

`RayCast2D` and `ShapeCast2D` don't care what layer their parent is on. They have their
own `collision_mask`, and by default `collide_with_areas` is **false** — so a ray aimed
at a hurtbox sees nothing. The same goes for direct space queries:

```gdscript
func line_of_sight(from: Vector2, to: Vector2) -> bool:
	var query := PhysicsRayQueryParameters2D.create(from, to)
	query.collision_mask = 1 << (PhysicsLayers.WORLD - 1) # bitmask, see tip 3
	query.exclude = [get_rid()]
	var hit := get_world_2d().direct_space_state.intersect_ray(query)
	return hit.is_empty()
```

Note the `1 << (n - 1)`: the query wants the raw bitmask, not the 1-based number.

## 7. TileMap walls get their layer from the TileSet

Setting the layer on a `TileMapLayer` node's inspector won't help if the walls still
pass through things. Tile collision lives in the **TileSet** resource: open it, look
under **Physics Layers**, and set `collision_layer` / `collision_mask` there. Each
physics layer of the TileSet has its own pair — a one-way platform layer and a solid
wall layer can sit on different bits.

Turn on **Debug → Visible Collision Shapes** while you check; if the tile shapes don't
draw, the tiles have no collision polygons painted yet and no layer setting will fix it.

## The pattern behind all seven

Every tip above is bookkeeping: deciding, once, who is what and who looks for whom, and
then never letting a raw number decide it again. For combat specifically, that table
in tip 1 is the part people rebuild in every project — hitbox masks, hurtbox layers,
which team hits which.

Saltmire Hitbox Lite is a free, MIT `Hitbox2D` / `Hurtbox2D` pair that handles that
table for you: you set a team on each box and it wires the layers, so a player's sword
only finds enemy hurtboxes without you touching a single checkbox. If you'd rather keep
your own layer plan, the tips above are everything it does under the hood.
