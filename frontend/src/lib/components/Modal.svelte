<!--
    Thin wrapper over Bits UI's Dialog (focus trap, scroll lock, Esc/overlay
    close, ARIA — all handled upstream). Same `open` / `title` / `onclose` /
    `width` API as before. Styling is plain Tailwind utilities (our @theme
    tokens), since classes passed to Bits UI components don't get Svelte's
    scope hash.
-->
<script lang="ts">
    import { Dialog } from 'bits-ui'
    import type { Snippet } from 'svelte'

    interface Props {
        open: boolean
        title?: string
        onclose: () => void
        width?: string
        children: Snippet
    }

    let {
        open = $bindable(),
        title,
        onclose,
        width = 'min(480px, 100%)',
        children,
    }: Props = $props()

    function handleOpenChange(next: boolean) {
        if (!next) {
            onclose()
        }
    }
</script>

<Dialog.Root bind:open onOpenChange={handleOpenChange}>
    <Dialog.Portal>
        <Dialog.Overlay class="fixed inset-0 z-9998 bg-black/45" />
        <Dialog.Content
            class="fixed left-1/2 top-1/2 z-9999 max-h-[calc(100vh-2rem)] w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 overflow-auto rounded-[0.9rem] border border-bark-600 bg-bark-800 p-4 text-ink-200"
            style="max-width: {width}"
        >
            <div class="mb-3 flex items-center justify-between">
                <Dialog.Title class="m-0 text-[1.1rem] text-ink-100">
                    {title ?? ''}
                </Dialog.Title>
                <Dialog.Close
                    class="flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-[0.45rem] border border-bark-600 bg-bark-850 text-ink-100 hover:bg-bark-730"
                    aria-label="Close"
                >
                    ✕
                </Dialog.Close>
            </div>
            {@render children()}
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
