<script lang="ts">
	import { Text, Sprite } from 'pixi-svelte';
	import { Button, type ButtonProps } from 'components-pixi';
	import { stateModal, stateBet, stateBetDerived } from 'state-shared';

	import { UI_BASE_FONT_SIZE, UI_BASE_SIZE } from '../constants';
	import { getContext } from '../context';
	import { i18nDerived } from '../i18n/i18nDerived';

	const props: Partial<Omit<ButtonProps, 'children'>> = $props();
	const { stateXstateDerived, eventEmitter } = getContext();
	// bigger than the other HUD buttons on purpose -- AI-generated treasure chest art
	// (see stake_engine/README.md), replacing the plain gold rounded-rect background
	const sizes = { width: UI_BASE_SIZE * 2, height: UI_BASE_SIZE * 2 };
	const disabled = $derived(!stateXstateDerived.isIdle());
	const active = $derived(stateBetDerived.activeBetMode()?.type === 'activate');

	const openModal = () => (stateModal.modal = { name: 'buyBonus' });
	const disableActiveBetMode = () => (stateBet.activeBetModeKey = 'BASE');
	const onpress = () => {
		eventEmitter.broadcast({ type: 'soundPressGeneral' });

		if (active) {
			disableActiveBetMode();
		} else {
			openModal();
		}
	};

	const getState = (value: {
		active: boolean;
		disabled: boolean;
		hovered: boolean;
		pressed: boolean;
	}) => {
		if (value.disabled) return 'disabled' as const;
		if (value.pressed) return 'pressed' as const;
		if (value.hovered) return 'hovered' as const;
		if (value.active) return 'active' as const;
		return 'default' as const;
	};
</script>

<Button {...props} {sizes} {disabled} {onpress}>
	{#snippet children({ center, hovered, pressed })}
		{@const state = getState({
			active,
			disabled,
			hovered,
			pressed,
		})}

		<Sprite
			key="vcBuyBonusChest"
			{...center}
			anchor={0.5}
			width={sizes.width}
			height={sizes.height}
			alpha={disabled ? 0.5 : 1}
			tint={active ? 0xffe9a8 : 0xffffff}
		/>

		<Text
			{...center}
			y={center.y + sizes.height * 0.42}
			anchor={0.5}
			text={state === 'active' ? i18nDerived.disable() : i18nDerived.buyBonus()}
			style={{
				align: 'center',
				wordWrap: true,
				wordWrapWidth: sizes.width,
				fontFamily: 'proxima-nova',
				fontWeight: '800',
				fontSize: UI_BASE_FONT_SIZE * 1.1,
				fill: 0xffe9a8,
				stroke: { color: 0x2a1600, width: 4 },
			}}
		/>
	{/snippet}
</Button>
