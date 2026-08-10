<script lang="ts">
	import { Rectangle, Sprite } from 'pixi-svelte';

	import { getContext } from '../game/context';

	const context = getContext();
</script>

<Rectangle {...context.stateLayoutDerived.canvasSizes()} backgroundColor={0x000000} zIndex={-4} />

<Sprite key="vcBackground" {...context.stateLayoutDerived.canvasSizes()} zIndex={-3} />
