<!--
    Thin wrapper over Bits UI's Select (headless, accessible, Floating-UI
    positioned, portaled — so it works on iOS Safari and escapes
    `overflow: hidden` ancestors like modals). We keep the project's dark
    styling and a simple `items` / `value` / `onchange` API; Bits UI owns the
    keyboard / focus / ARIA / positioning behaviour.

    Styling is plain Tailwind utilities (our @theme tokens) rather than a scoped
    <style> block: classes passed to Bits UI components don't receive Svelte's
    scope hash, so scoped selectors wouldn't apply. The `select-base` marker is
    kept for the page-level hook in analytics (`.controls .select-base`).

    Bits UI Select works in string values, so we map our typed (string | number)
    values to/from strings at the boundary.
-->
<script lang="ts" module>
    export interface SelectItem<T extends string | number = string | number> {
        value: T
        label: string
        icon?: string | null
    }
</script>

<script lang="ts" generics="T extends string | number">
    import { Select } from 'bits-ui'

    interface Props {
        items: SelectItem<T>[]
        value?: T
        onchange?: (value: T) => void
        class?: string
        id?: string
        disabled?: boolean
    }

    let {
        items,
        value = $bindable<T>(),
        class: className = '',
        onchange,
        id,
        disabled,
    }: Props = $props()

    let selected = $state(value === undefined ? '' : String(value))

    // Keep the internal string in sync when the parent changes `value`.
    $effect(() => {
        selected = value === undefined ? '' : String(value)
    })

    const selectedItem = $derived(items.find((item) => String(item.value) === selected))

    function handleValueChange(next: string) {
        const match = items.find((item) => String(item.value) === next)
        if (match) {
            onchange?.(match.value)
        }
    }
</script>

<Select.Root
    type="single"
    bind:value={selected}
    onValueChange={handleValueChange}
    {disabled}
>
    <Select.Trigger
        {id}
        class="select-base group inline-flex max-w-full cursor-pointer items-center gap-[0.4rem] text-left data-disabled:cursor-not-allowed data-disabled:opacity-60 {className}"
    >
        <span class="inline-flex min-w-0 flex-1 items-center gap-[0.35rem]">
            {#if selectedItem?.icon}
                <span class="shrink-0 text-base leading-[1.4]" aria-hidden="true">
                    {selectedItem.icon}
                </span>
            {/if}
            <span class="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap">
                {selectedItem?.label ?? ''}
            </span>
        </span>
        <span
            class="shrink-0 text-ink-400 transition-transform duration-150 group-data-[state=open]:rotate-90"
            aria-hidden="true"
        >
            ›
        </span>
    </Select.Trigger>
    <Select.Portal>
        <Select.Content
            class="z-[10000] max-h-[280px] min-w-[var(--bits-select-anchor-width)] overflow-y-auto rounded-lg border border-ink-600 bg-ink-900 p-1 shadow-[0_10px_30px_rgba(0,0,0,0.45)]"
        >
            <Select.Viewport>
                {#each items as item (item.value)}
                    <Select.Item
                        class="flex cursor-pointer items-start gap-[0.4rem] rounded-[0.35rem] px-[0.6rem] py-[0.4rem] text-ink-100 outline-none data-[highlighted]:bg-bark-800 data-[selected]:bg-accent-900"
                        value={String(item.value)}
                        label={item.label}
                    >
                        {#if item.icon}
                            <span
                                class="shrink-0 text-base leading-[1.4]"
                                aria-hidden="true"
                            >
                                {item.icon}
                            </span>
                        {/if}
                        <span class="min-w-0">{item.label}</span>
                    </Select.Item>
                {/each}
            </Select.Viewport>
        </Select.Content>
    </Select.Portal>
</Select.Root>
