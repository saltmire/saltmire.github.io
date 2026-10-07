---
title: GPUParticles2D vs CPUParticles2D in Godot 4 — which and when
description: A practical Godot 4 comparison of GPUParticles2D and CPUParticles2D — what each one can do, how they behave on the Compatibility renderer and web exports, the first-burst stutter, and a simple rule for picking the right node for hit sparks, explosions and ambient effects.
slug: godot-4-gpuparticles2d-vs-cpuparticles2d
date: 2026-10-07
product_name: Saltmire Spark
product_url: https://saltmire.itch.io/saltmire-spark
---

You open the Add Node dialog, type "particles", and Godot 4 offers you two nodes that
look identical in the viewport: `GPUParticles2D` and `CPUParticles2D`. Both emit
sprites, both have `amount`, `lifetime`, `one_shot` and `explosiveness`. The names tell
you *where* the simulation runs, but not what that means for your game. Here's the
practical difference, and the rule I use to pick.

## GPUParticles2D: the simulation lives in a shader

`GPUParticles2D` moves every particle on the graphics card. Its behaviour comes from a
`ParticleProcessMaterial` — velocity, gravity, scale curves, color ramps — which Godot
compiles into a shader.

```gdscript
var p := GPUParticles2D.new()
var mat := ParticleProcessMaterial.new()
mat.direction = Vector3(0, -1, 0)
mat.spread = 45.0
mat.initial_velocity_min = 120.0
mat.initial_velocity_max = 220.0
mat.gravity = Vector3(0, 400, 0)
p.process_material = mat
p.amount = 16
p.lifetime = 0.5
p.one_shot = true
p.explosiveness = 1.0
add_child(p)
p.restart()
```

What it gives you that the CPU node doesn't: **turbulence**, **collision** against
`LightOccluder2D` shapes, **sub-emitters** (a spark that spawns smoke when it dies),
**trails**, and custom particle shaders. It also scales: thousands of particles cost
the CPU almost nothing, because the CPU never touches them.

What it costs you:

- **A `visibility_rect` you must maintain.** The node is culled by that rectangle, and
  the default is small. Particles that fly outside it simply vanish.
- **A first-use hitch.** The process material is a shader, and shaders compile the first
  time they're used. On many machines the very first explosion stutters for a frame. You
  can hide it by firing each effect once off-screen during your loading screen.
- **Renderer quirks.** GPU particles only work on the Compatibility renderer (the one
  web exports and many low-end Android devices use) since Godot 4.2, and that path is
  less battle-tested than Forward+. If you target the web, test there early.

## CPUParticles2D: the simulation lives in a script loop

`CPUParticles2D` does the same job in engine code on the CPU. There is no process
material — every setting is a property directly on the node:

```gdscript
var p := CPUParticles2D.new()
p.direction = Vector2(0, -1)
p.spread = 45.0
p.initial_velocity_min = 120.0
p.initial_velocity_max = 220.0
p.gravity = Vector2(0, 400)
p.amount = 16
p.lifetime = 0.5
p.one_shot = true
p.explosiveness = 1.0
add_child(p)
p.restart()
```

That's the whole point of it: **it behaves the same everywhere**. Forward+, Mobile,
Compatibility, web, old integrated GPUs — the simulation is identical because it never
depended on the graphics card. There's no shader to compile, so no first-burst hitch,
and no `visibility_rect` to babysit — the bounds are computed for you.

The trade-off is a smaller feature set (no turbulence, collision, sub-emitters or trails)
and a cost that grows with particle count. Every particle is updated on the main CPU
every frame. Sixteen sparks per hit is nothing. Ten thousand snowflakes is not.

## The comparison

| | GPUParticles2D | CPUParticles2D |
|---|---|---|
| Where it simulates | GPU (shader) | CPU (engine loop) |
| Configuration | `ParticleProcessMaterial` resource | properties on the node |
| Cost of 10,000 particles | low on CPU | high on CPU |
| Cost of 15 small bursts | a draw + a shader each | tiny |
| Turbulence, collision, sub-emitters, trails | yes | no |
| First-use shader hitch | yes (pre-warm it) | no |
| `visibility_rect` culling | manual, easy to get wrong | automatic |
| Compatibility renderer / web | supported since 4.2, test it | works everywhere |
| `restart()`, `one_shot`, `finished` signal | yes | yes |

## Switching costs one click

You don't have to commit forever. Select a `GPUParticles2D` in the editor and the
toolbar's **GPUParticles2D** menu has **Convert to CPUParticles2D**. The CPU node has the
reverse option in its own toolbar menu. Features the CPU node lacks are dropped in the
conversion, so commit the scene first and compare.

If you build effects in code and ship to several platforms, you can also pick at runtime:

```gdscript
func make_burst_node() -> Node2D:
	var method: String = ProjectSettings.get_setting("rendering/renderer/rendering_method")
	if method == "gl_compatibility" or OS.has_feature("web"):
		return CPUParticles2D.new()
	return GPUParticles2D.new()
```

If you go this route, keep your tuning values in one place (a dictionary or a custom
resource) so both branches read the same numbers.

## The rule that decides it

Ask two questions:

1. **Is it a big, long-lived or fancy effect?** Rain, snow, a fog bank, a magic vortex
   with turbulence, sparks that bounce off walls. That's `GPUParticles2D`.
2. **Is it a small, short burst that fires a lot?** Hit sparks, pickup glitter, dust from
   a footstep, a coin pop. That's `CPUParticles2D`. Especially if you export to the web.

Most 2D action games end up with both: a few big GPU systems for ambience, and many tiny
CPU bursts for feedback. The bursts are where the work really piles up, though — every
new enemy hit, pickup and death wants its own tuned node, its own `one_shot` setup, and
its own cleanup when it's done.

That's the part Saltmire Spark takes off your plate. It's a free, MIT-licensed autoload
that fires a tuned 2D burst in one line (`Spark.burst(pos, "hit")`) and frees itself
afterwards. It doesn't use either particle node — the particles are drawn procedurally —
so there's no process material, no `visibility_rect` and no renderer difference to think
about.
