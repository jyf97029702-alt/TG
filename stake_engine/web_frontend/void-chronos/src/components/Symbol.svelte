<script lang="ts">
	import SymbolGraphic from './SymbolGraphic.svelte';
	import type { SymbolState, RawSymbol } from '../game/types';

	type Props = {
		x?: number;
		y?: number;
		state: SymbolState;
		rawSymbol: RawSymbol;
		oncomplete?: () => void;
		loop?: boolean;
	};

	const props: Props = $props();

	// Procedural symbols have no Spine 'complete' event to drive state transitions
	// (e.g. 'land' -> 'static', 'win' -> next cascade step) -- fire oncomplete on a
	// short fixed delay instead, so callers waiting on it don't stall forever.
	$effect(() => {
		props.state;
		if (!props.oncomplete) return;
		const id = setTimeout(() => props.oncomplete?.(), 180);
		return () => clearTimeout(id);
	});
</script>

<SymbolGraphic x={props.x} y={props.y} rawSymbol={props.rawSymbol} />
