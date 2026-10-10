import { describe, expect, mock, test } from 'bun:test'

import { render, screen, waitFor } from '@testing-library/svelte'
import userEvent from '@testing-library/user-event'
import { createRawSnippet } from 'svelte'

import ConfirmDialog from './ConfirmDialog.svelte'

const warning = createRawSnippet(() => ({ render: () => '<p>Gone for good.</p>' }))

function renderConfirm(extra: { busy?: boolean; disabled?: boolean } = {}) {
    const onconfirm = mock(() => {})
    const onclose = mock(() => {})
    render(ConfirmDialog, {
        open: true,
        title: 'Delete product',
        confirmLabel: 'Delete',
        onconfirm,
        onclose,
        children: warning,
        ...extra,
    })
    return { onconfirm, onclose, user: userEvent.setup() }
}

describe('ConfirmDialog', () => {
    test('is an alertdialog, labeled and described', () => {
        renderConfirm()
        const dialog = screen.getByRole('alertdialog', { name: 'Delete product' })
        expect(dialog.getAttribute('aria-describedby')).toBeTruthy()
        expect(dialog.textContent).toContain('Gone for good.')
    })

    // The point of the AlertDialog: a stray Enter must not delete.
    test('focus starts on Cancel, so Enter cancels', async () => {
        const { onconfirm, onclose, user } = renderConfirm()
        const cancel = screen.getByRole('button', { name: 'Cancel' })
        await waitFor(() => expect(document.activeElement).toBe(cancel))
        await user.keyboard('{Enter}')
        expect(onclose).toHaveBeenCalledTimes(1)
        expect(onconfirm).not.toHaveBeenCalled()
    })

    test('confirm calls onconfirm and leaves closing to the caller', async () => {
        const { onconfirm, onclose, user } = renderConfirm()
        await user.click(screen.getByRole('button', { name: 'Delete' }))
        expect(onconfirm).toHaveBeenCalledTimes(1)
        expect(onclose).not.toHaveBeenCalled()
    })

    test('busy disables both buttons; disabled only the confirm', () => {
        renderConfirm({ busy: true })
        expect(screen.getByRole('button', { name: 'Cancel' })).toHaveProperty(
            'disabled',
            true,
        )
        expect(screen.getByRole('button', { name: 'Delete' })).toHaveProperty(
            'disabled',
            true,
        )
    })

    test('busy: Escape does not close mid-request', async () => {
        const { onclose, user } = renderConfirm({ busy: true })
        await user.keyboard('{Escape}')
        expect(onclose).not.toHaveBeenCalled()
    })

    test('disabled keeps Cancel usable', () => {
        renderConfirm({ disabled: true })
        expect(screen.getByRole('button', { name: 'Cancel' })).toHaveProperty(
            'disabled',
            false,
        )
        expect(screen.getByRole('button', { name: 'Delete' })).toHaveProperty(
            'disabled',
            true,
        )
    })
})
