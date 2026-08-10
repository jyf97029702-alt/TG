<script lang="ts" module>
	import * as PIXI from 'pixi.js';

	type Palette = { top: number; bot: number; icon: number; glow: number };

	const PALETTE: Record<string, Palette> = {
		S1: { top: 0x1fd9ff, bot: 0x0b6b82, icon: 0xeafeff, glow: 0x22e5ff },
		S2: { top: 0x2be6b0, bot: 0x0a6b58, icon: 0xe9fff8, glow: 0x14b8a6 },
		S3: { top: 0x4d8dff, bot: 0x1c3f8c, icon: 0xeaf1ff, glow: 0x3b82f6 },
		S4: { top: 0xffd76b, bot: 0x9c6a10, icon: 0xfff6dd, glow: 0xf5c542 },
		S5: { top: 0x9b6bff, bot: 0x2e1064, icon: 0xd8c2ff, glow: 0x8b5cf6 },
		S6: { top: 0x39c7ff, bot: 0x8a5a12, icon: 0xfff0c9, glow: 0xf5c542 },
		S7: { top: 0xd4941e, bot: 0x3a2408, icon: 0xffe9b8, glow: 0xd4941e },
		S8: { top: 0x2a2a3f, bot: 0x05050c, icon: 0x9fe9ff, glow: 0x22e5ff },
		W: { top: 0xfff6d0, bot: 0xd6a417, icon: 0x3a2b00, glow: 0xffe27a },
		SC: { top: 0xf27bff, bot: 0x7a0d97, icon: 0xfff0ff, glow: 0xe347ff },
		P: { top: 0x22e5ff, bot: 0x7a3fd1, icon: 0xfff9e0, glow: 0xb26bff },
		C: { top: 0x27314c, bot: 0x05070d, icon: 0x8fe8ff, glow: 0x22e5ff },
	};

	function orbPalette(v: number): Palette {
		if (v >= 500) return { top: 0xff5fae, bot: 0x780d3d, icon: 0xfff0f7, glow: 0xff2f8f };
		if (v >= 50) return { top: 0xffcf5a, bot: 0x9c5c0a, icon: 0xfff6dd, glow: 0xf5c542 };
		return { top: 0x22e5ff, bot: 0x0a5a75, icon: 0xeafeff, glow: 0x22e5ff };
	}

	function regularPolygonPoints(cx: number, cy: number, r: number, sides: number, rotation = 0) {
		const pts: number[] = [];
		for (let i = 0; i < sides; i++) {
			const a = rotation + i * ((Math.PI * 2) / sides);
			pts.push(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
		}
		return pts;
	}

	function starPoints(cx: number, cy: number, rOuter: number, rInner: number, spikes: number, rotation = -Math.PI / 2) {
		const pts: number[] = [];
		for (let i = 0; i < spikes * 2; i++) {
			const r = i % 2 === 0 ? rOuter : rInner;
			const a = rotation + i * (Math.PI / spikes);
			pts.push(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
		}
		return pts;
	}

	// Draws the VOID CHRONOS symbol icons directly with PIXI.Graphics -- ported from the
	// standalone prototype (index.html's drawIcon) rather than Spine/sprite-sheet assets.
	export function drawSymbolIcon(g: PIXI.Graphics, name: string, value?: number) {
		const pal = name === 'O' ? orbPalette(value ?? 2) : (PALETTE[name] ?? PALETTE.S1);
		switch (name) {
			case 'S1':
				g.poly(regularPolygonPoints(0, 0, 24, 4, -Math.PI / 2)).fill(pal.icon).stroke({ width: 2, color: pal.glow, alpha: 0.9 });
				break;
			case 'S2':
				g.poly(regularPolygonPoints(0, 0, 23, 6)).fill(pal.icon);
				g.moveTo(-9, 0).lineTo(9, 0).moveTo(0, -9).lineTo(0, 9).stroke({ width: 2.5, color: pal.glow, alpha: 0.95 });
				break;
			case 'S3':
				g.poly(regularPolygonPoints(0, 0, 24, 5, -Math.PI / 2)).fill(pal.icon).stroke({ width: 2, color: pal.glow, alpha: 0.9 });
				break;
			case 'S4':
				g.circle(0, 0, 23).fill(pal.icon);
				g.circle(0, 0, 16).stroke({ width: 2.5, color: pal.glow, alpha: 1 });
				g.poly(starPoints(0, 0, 7, 3, 5)).fill({ color: pal.glow, alpha: 0.9 });
				break;
			case 'S5':
				g.ellipse(0, 0, 25, 15).fill(pal.icon);
				g.circle(0, 0, 9).fill(0x0b0018);
				g.circle(0, 0, 4.5).fill(pal.glow);
				break;
			case 'S6':
				g.circle(0, 0, 20).stroke({ width: 4, color: pal.icon, alpha: 1 });
				g.circle(0, 0, 12).stroke({ width: 3, color: pal.glow, alpha: 1 });
				g.circle(0, 0, 4).fill({ color: pal.icon, alpha: 0.9 });
				break;
			case 'S7': {
				const teeth = 8;
				for (let i = 0; i < teeth; i++) {
					const a = i * ((Math.PI * 2) / teeth);
					g.rect(Math.cos(a) * 20 - 3.5, Math.sin(a) * 20 - 3.5, 7, 7);
				}
				g.fill(pal.icon);
				g.circle(0, 0, 15).fill(pal.icon);
				g.circle(0, 0, 6).fill(0x1a1000);
				break;
			}
			case 'S8':
				g.roundRect(-16, -18, 32, 27, 13).fill(pal.icon);
				g.poly([-13, 7, -3, 7, -8, 20]).fill(pal.icon);
				g.poly([3, 7, 13, 7, 8, 20]).fill(pal.icon);
				g.circle(-7, -5, 4).fill(pal.glow);
				g.circle(7, -5, 4).fill(pal.glow);
				break;
			case 'W':
				g.poly(starPoints(0, 0, 26, 11, 8)).fill(pal.icon).stroke({ width: 2, color: pal.bot, alpha: 0.85 });
				g.circle(0, 0, 12).stroke({ width: 1.6, color: pal.bot, alpha: 0.9 });
				break;
			case 'SC':
				g.circle(0, 0, 26).stroke({ width: 2.4, color: pal.glow, alpha: 0.9 });
				g.poly([-13, -16, 13, -16, 3, 0, 13, 16, -13, 16, -3, 0]).fill(pal.icon).stroke({ width: 1.5, color: 0xffe9a8, alpha: 0.9 });
				g.moveTo(-3, 0).lineTo(3, 0).stroke({ width: 1.4, color: pal.glow, alpha: 1 });
				break;
			case 'P':
				g.circle(0, 0, 21).stroke({ width: 4, color: pal.top, alpha: 1 });
				g.circle(0, 0, 13).stroke({ width: 2.4, color: pal.bot, alpha: 0.9 });
				g.circle(0, 0, 6).stroke({ width: 1.5, color: pal.icon, alpha: 0.85 });
				break;
			case 'C':
				g.circle(0, 0, 14).stroke({ width: 1.4, color: pal.glow, alpha: 0.9 }).fill(0x02040a);
				g.poly(regularPolygonPoints(0, 0, 4, 4, -Math.PI / 2)).fill({ color: pal.glow, alpha: 0.9 });
				for (let i = 0; i < 8; i++) {
					const a = i * ((Math.PI * 2) / 8);
					g.moveTo(Math.cos(a) * 24, Math.sin(a) * 24)
						.lineTo(Math.cos(a) * 15, Math.sin(a) * 15)
						.stroke({ width: 2, color: pal.glow, alpha: 0.85 });
				}
				break;
			case 'O':
				g.circle(0, 0, 20).fill(pal.icon).stroke({ width: 2, color: pal.glow, alpha: 1 });
				g.ellipse(-6, -8, 7, 5).fill({ color: 0xffffff, alpha: 0.4 });
				break;
			default:
				g.circle(0, 0, 20).fill(pal.icon);
		}
	}

	export function symbolGlowColor(name: string, value?: number): number {
		return (name === 'O' ? orbPalette(value ?? 2) : (PALETTE[name] ?? PALETTE.S1)).glow;
	}

	// AI-generated art available for these symbols (see stake_engine/README.md)
	export const SYMBOL_ART_KEY: Record<string, string> = {
		S1: 'vcDiamond',
		S2: 'vcHexagon',
		S3: 'vcPentagon',
		S4: 'vcRune',
		S5: 'vcCrystal',
		S6: 'vcGemPurple',
		S7: 'vcClock',
		S8: 'vcSkull',
		W: 'vcEye',
		SC: 'vcStar',
		P: 'vcPortalCircle',
		C: 'vcUrn',
	};

	// O (Orb) picks its art by value tier, matching orbPalette()'s thresholds
	function orbArtKey(value: number): string {
		if (value >= 500) return 'vcOrbHigh';
		if (value >= 50) return 'vcOrbMid';
		return 'vcOrbLow';
	}
</script>

<script lang="ts">
	import { Container, Graphics, Sprite, Text } from 'pixi-svelte';
	import type { RawSymbol } from '../game/types';

	type Props = { x?: number; y?: number; rawSymbol: RawSymbol };
	const props: Props = $props();

	const name = $derived(props.rawSymbol.name as string);
	const value = $derived(props.rawSymbol.multiplier);
	const glow = $derived(symbolGlowColor(name, value));
	const artKey = $derived(name === 'O' ? orbArtKey(value ?? 2) : SYMBOL_ART_KEY[name]);
	const label = $derived(
		name === 'SC' ? 'SCATTER' : name === 'W' ? 'WILD' : name === 'P' ? 'PORTAL' : name === 'C' ? 'COLLECT' : '',
	);
</script>

<Container x={props.x} y={props.y}>
	<Graphics
		draw={(g) => {
			g.clear();
			g.circle(0, 0, 34).fill({ color: glow, alpha: 0.14 });
		}}
		filters={[new PIXI.BlurFilter({ strength: 8 })]}
	/>
	{#if artKey}
		<Sprite key={artKey} anchor={0.5} width={76} height={76} />
	{:else}
		<Graphics draw={(g) => drawSymbolIcon(g, name, value)} tint={glow} alpha={0.55} scale={1.15} />
		<Graphics draw={(g) => drawSymbolIcon(g, name, value)} />
	{/if}
	{#if name === 'O'}
		<Text
			text={`${value ?? ''}x`}
			anchor={0.5}
			y={26}
			style={{ fontFamily: 'Georgia, serif', fontWeight: '800', fontSize: 14, fill: (value ?? 0) >= 500 ? 0xffe4f2 : (value ?? 0) >= 50 ? 0x3a2400 : 0x00323c }}
		/>
	{/if}
	{#if label}
		<Text
			text={label}
			anchor={0.5}
			y={34}
			style={{ fontFamily: 'Segoe UI, sans-serif', fontWeight: '800', fontSize: 8, letterSpacing: 1, fill: 0xffffff }}
		/>
	{/if}
</Container>
