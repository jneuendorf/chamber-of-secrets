<!--
    Custom button + listbox select.

    Hand-rolled rather than using CSS `appearance: base-select`: that API has
    no iOS Safari support (and none in Firefox / desktop Safari) as of 2026,
    and this is a mobile-first app. A button + fixed-positioned listbox works
    everywhere and escapes `overflow: hidden` ancestors (e.g. modals).
    See ROADMAP WL-3.4 — candidate for migration to a headless library.

    Follows the ARIA combobox + aria-activedescendant pattern: focus stays on
    the trigger and all keyboard handling lives there, so the options are
    intentionally mouse-only (keyboard reaches them via the trigger).
-->
<script lang="ts" module>
    export interface SelectItem<T extends string | number = string | number> {
        value: T
        label: string
        icon?: string | null
    }

    let uid = 0
</script>

<script lang="ts" generics="T extends string | number">
    import { tick } from 'svelte'
    import type { HTMLButtonAttributes } from 'svelte/elements'

    interface Props extends Omit<HTMLButtonAttributes, 'value' | 'onchange'> {
        items: SelectItem<T>[]
        value?: T
        onchange?: (value: T) => void
    }

    let {
        items,
        value = $bindable<T>(),
        class: className = '',
        onchange,
        ...restProps
    }: Props = $props()

    const listboxId = `select-listbox-${uid++}`

    let open = $state(false)
    let highlightedIndex = $state(-1)
    let triggerEl: HTMLButtonElement | undefined = $state()
    let listboxEl: HTMLDivElement | undefined = $state()
    let menuStyle = $state('')
    let typeahead = ''
    let typeaheadTimer: ReturnType<typeof setTimeout> | undefined

    const selectedItem = $derived(items.find((item) => item.value === value))
    const selectedIndex = $derived(items.findIndex((item) => item.value === value))

    function positionMenu() {
        if (!triggerEl) {
            return
        }
        const rect = triggerEl.getBoundingClientRect()
        const spaceBelow = window.innerHeight - rect.bottom - 8
        const maxHeight = Math.max(Math.min(spaceBelow, 280), 120)
        menuStyle =
            `position: fixed; top: ${rect.bottom + 4}px; left: ${rect.left}px; ` +
            `min-width: ${rect.width}px; max-height: ${maxHeight}px;`
    }

    function scrollHighlightedIntoView() {
        const optionEl = listboxEl?.children[highlightedIndex] as
            | HTMLElement
            | undefined
        optionEl?.scrollIntoView({ block: 'nearest' })
    }

    async function openMenu() {
        if (restProps.disabled || open) {
            return
        }
        open = true
        highlightedIndex = selectedIndex >= 0 ? selectedIndex : 0
        positionMenu()
        await tick()
        scrollHighlightedIntoView()
    }

    function closeMenu(refocus = true) {
        if (!open) {
            return
        }
        open = false
        highlightedIndex = -1
        if (refocus) {
            triggerEl?.focus()
        }
    }

    function selectItem(item: SelectItem<T>) {
        value = item.value
        onchange?.(item.value)
        closeMenu()
    }

    function moveHighlight(delta: number) {
        if (items.length === 0) {
            return
        }
        highlightedIndex = (highlightedIndex + delta + items.length) % items.length
        scrollHighlightedIntoView()
    }

    function applyTypeahead(char: string) {
        clearTimeout(typeaheadTimer)
        typeahead += char.toLowerCase()
        typeaheadTimer = setTimeout(() => {
            typeahead = ''
        }, 500)
        const match = items.findIndex((item) =>
            item.label.toLowerCase().startsWith(typeahead),
        )
        if (match >= 0) {
            highlightedIndex = match
            scrollHighlightedIntoView()
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault()
                open ? moveHighlight(1) : openMenu()
                break
            case 'ArrowUp':
                event.preventDefault()
                open ? moveHighlight(-1) : openMenu()
                break
            case 'Enter':
            case ' ':
                event.preventDefault()
                if (!open) {
                    openMenu()
                } else {
                    const item = items[highlightedIndex]
                    if (item) {
                        selectItem(item)
                    }
                }
                break
            case 'Escape':
                if (open) {
                    event.preventDefault()
                    closeMenu()
                }
                break
            case 'Tab':
                closeMenu(false)
                break
            case 'Home':
                if (open) {
                    event.preventDefault()
                    highlightedIndex = 0
                    scrollHighlightedIntoView()
                }
                break
            case 'End':
                if (open) {
                    event.preventDefault()
                    highlightedIndex = items.length - 1
                    scrollHighlightedIntoView()
                }
                break
            default:
                if (event.key.length === 1 && !event.metaKey && !event.ctrlKey) {
                    applyTypeahead(event.key)
                }
        }
    }

    function handlePointerDown(event: PointerEvent) {
        const target = event.target as Node
        if (open && !triggerEl?.contains(target) && !listboxEl?.contains(target)) {
            closeMenu(false)
        }
    }

    $effect(() => {
        if (!open) {
            return
        }
        window.addEventListener('pointerdown', handlePointerDown, true)
        window.addEventListener('resize', positionMenu)
        window.addEventListener('scroll', positionMenu, true)
        return () => {
            window.removeEventListener('pointerdown', handlePointerDown, true)
            window.removeEventListener('resize', positionMenu)
            window.removeEventListener('scroll', positionMenu, true)
        }
    })
</script>

<button
    bind:this={triggerEl}
    type="button"
    class="select-base {className}"
    role="combobox"
    aria-haspopup="listbox"
    aria-expanded={open}
    aria-controls={listboxId}
    aria-activedescendant={open && highlightedIndex >= 0
        ? `${listboxId}-opt-${highlightedIndex}`
        : undefined}
    onclick={() => (open ? closeMenu() : openMenu())}
    onkeydown={handleKeydown}
    {...restProps}
>
    <span class="trigger-content">
        {#if selectedItem?.icon}
            <span class="option-icon" aria-hidden="true">{selectedItem.icon}</span>
        {/if}
        <span class="trigger-label">{selectedItem?.label ?? ''}</span>
    </span>
    <span class="chevron" class:open aria-hidden="true">›</span>
</button>

{#if open}
    <div
        bind:this={listboxEl}
        id={listboxId}
        class="menu"
        role="listbox"
        style={menuStyle}
    >
        {#each items as item, index (item.value)}
            <button
                id="{listboxId}-opt-{index}"
                type="button"
                class="option"
                class:highlighted={index === highlightedIndex}
                role="option"
                tabindex={-1}
                aria-selected={item.value === value}
                onclick={() => selectItem(item)}
                onpointermove={() => (highlightedIndex = index)}
            >
                {#if item.icon}
                    <span class="option-icon" aria-hidden="true">{item.icon}</span>
                {/if}
                <span class="option-label">{item.label}</span>
            </button>
        {/each}
    </div>
{/if}

<style>
    .select-base {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        width: fit-content;
        max-width: 100%;
        cursor: pointer;
        font: inherit;
        text-align: left;
    }

    .select-base:disabled {
        cursor: not-allowed;
        opacity: 0.6;
    }

    .trigger-content {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        min-width: 0;
        flex: 1;
    }

    .trigger-label {
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .chevron {
        flex-shrink: 0;
        color: #9ca3af;
        transition: transform 0.15s ease;
    }

    .chevron.open {
        transform: rotate(90deg);
    }

    .menu {
        margin: 0;
        padding: 0.25rem;
        background: #111827;
        border: 1px solid #4b5563;
        border-radius: 8px;
        overflow-y: auto;
        z-index: 60;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
    }

    .option {
        display: flex;
        align-items: flex-start;
        gap: 0.4rem;
        width: 100%;
        padding: 0.4rem 0.6rem;
        border: 0;
        border-radius: 0.35rem;
        background: transparent;
        color: #f3f4f6;
        font: inherit;
        text-align: left;
        cursor: pointer;
    }

    .option.highlighted {
        background: #2f2a22;
    }

    .option[aria-selected='true'] {
        background: #1a1a2e;
    }

    .option-icon {
        font-size: 1rem;
        line-height: 1.4;
        flex-shrink: 0;
    }

    .option-label {
        min-width: 0;
    }
</style>
