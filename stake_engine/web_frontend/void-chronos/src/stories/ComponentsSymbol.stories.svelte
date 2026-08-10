<script lang="ts" module>
	import { defineMeta } from '@storybook/addon-svelte-csf';

	const { Story } = defineMeta({
		title: 'Components/<Symbol>',
		component: Symbol,
		args: {
			x: 100,
			y: 100,
			rawSymbol: { name: 'SC', scatter: true },
			state: 'static',
		},
	});
</script>

<script lang="ts">
	import { Container, Text } from 'pixi-svelte';
	import { StoryPixiApp } from 'components-storybook';

	import Symbol from '../components/Symbol.svelte';
	import { SYMBOL_STATES } from '../game/types';
	import assets from '../game/assets';

	const BASE = 180;

	const SYMBOLS_LEFT = [
		{ name: 'SC', scatter: true },
		{ name: 'W', wild: true },
		{ name: 'P', portal: true },
		{ name: 'C', collector: true },
		{ name: 'O', multiplier: 2 },
		{ name: 'O', multiplier: 25 },
		{ name: 'O', multiplier: 100 },
		{ name: 'O', multiplier: 1000 },
	];

	const SYMBOLS_RIGHT = [
		{ name: 'S1' },
		{ name: 'S2' },
		{ name: 'S3' },
		{ name: 'S4' },
		{ name: 'S5' },
		{ name: 'S6' },
		{ name: 'S7' },
		{ name: 'S8' },
	];
</script>

<Story name="component">
	{#snippet template(args)}
		<StoryPixiApp {assets}>
			<Symbol {...args} oncomplete={() => console.log('complete')} />
		</StoryPixiApp>
	{/snippet}
</Story>

<Story name="symbols">
	{#snippet template()}
		<StoryPixiApp {assets}>
			<Container scale={0.5}>
				{#each SYMBOLS_LEFT as symbol, rowIndex}
					{#each SYMBOL_STATES as state, columnIndex}
						{@const x = (columnIndex + 1) * BASE}
						{@const y = (rowIndex + 1) * BASE}
						<Text {x} y={y - 100} anchor={{ x: 0.5, y: 0 }} text={`${symbol.name}: ${state}`} />
						<Symbol {x} {y} rawSymbol={symbol} {state} loop />
					{/each}
				{/each}
			</Container>

			<Container scale={0.5} x={550}>
				{#each SYMBOLS_RIGHT as symbol, rowIndex}
					{#each SYMBOL_STATES as state, columnIndex}
						{@const x = (columnIndex + 1) * BASE}
						{@const y = (rowIndex + 1) * BASE}
						<Text {x} y={y - 100} anchor={{ x: 0.5, y: 0 }} text={`${symbol.name}: ${state}`} />
						<Symbol {x} {y} rawSymbol={symbol} {state} loop />
					{/each}
				{/each}
			</Container>
		</StoryPixiApp>
	{/snippet}
</Story>
