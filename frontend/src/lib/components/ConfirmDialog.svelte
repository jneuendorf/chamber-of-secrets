<!--
    Destructive confirm over Bits UI's AlertDialog (WL-6.4): announced as
    `alertdialog`, an outside tap doesn't dismiss it, and focus starts on
    Cancel so a stray Enter can't delete. Styled like `Modal`.
-->
<script lang="ts">
    import { AlertDialog } from 'bits-ui'
    import type { Snippet } from 'svelte'
    import { _ } from 'svelte-i18n'

    interface Props {
        open: boolean
        title: string
        confirmLabel: string
        onconfirm: () => void
        onclose: () => void
        /** Disables both buttons, e.g. while the request runs. */
        busy?: boolean
        /** Disables just the confirm button, e.g. until a choice is made. */
        disabled?: boolean
        /** Merge isn't a delete: it gets the primary color, not danger. */
        tone?: 'danger' | 'primary'
        children?: Snippet
    }

    let {
        open,
        title,
        confirmLabel,
        onconfirm,
        onclose,
        busy = false,
        disabled = false,
        tone = 'danger',
        children,
    }: Props = $props()

    let cancelButton = $state<HTMLButtonElement | null>(null)
</script>

<AlertDialog.Root {open} onOpenChange={(next) => !next && onclose()}>
    <AlertDialog.Portal>
        <AlertDialog.Overlay class="fixed inset-0 z-9998 bg-black/45" />
        <AlertDialog.Content
            class="fixed left-1/2 top-1/2 z-9999 max-h-[calc(100vh-2rem)] w-[calc(100%-2rem)] max-w-120 -translate-x-1/2 -translate-y-1/2 overflow-auto rounded-[0.9rem] border border-bark-600 bg-bark-800 p-4 text-ink-200"
            onOpenAutoFocus={(event) => {
                event.preventDefault()
                cancelButton?.focus()
            }}
        >
            <AlertDialog.Title class="m-0 mb-3 text-[1.1rem] text-ink-100">
                {title}
            </AlertDialog.Title>
            {#if children}
                <AlertDialog.Description class="text-ink-200">
                    {@render children()}
                </AlertDialog.Description>
            {/if}
            <div class="mt-4 flex justify-end gap-2">
                <AlertDialog.Cancel
                    bind:ref={cancelButton}
                    disabled={busy}
                    class="rounded-lg border border-bark-600 bg-bark-850 px-4 py-2 text-sm font-semibold text-ink-200 disabled:opacity-50"
                >
                    {$_('common.cancel')}
                </AlertDialog.Cancel>
                <AlertDialog.Action
                    onclick={onconfirm}
                    disabled={busy || disabled}
                    class="rounded-lg border-0 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 {tone ===
                    'danger'
                        ? 'bg-danger-500'
                        : 'bg-accent-900'}"
                >
                    {confirmLabel}
                </AlertDialog.Action>
            </div>
        </AlertDialog.Content>
    </AlertDialog.Portal>
</AlertDialog.Root>
