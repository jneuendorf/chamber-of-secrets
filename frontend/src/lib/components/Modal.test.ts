import { describe, expect, mock, test } from 'bun:test'

import { render, screen } from '@testing-library/svelte'
import userEvent from '@testing-library/user-event'
import { createRawSnippet } from 'svelte'

import Modal from './Modal.svelte'

const body = createRawSnippet(() => ({ render: () => '<p>Modal body</p>' }))

function renderModal(open: boolean) {
    const onclose = mock(() => {})
    render(Modal, { open, title: 'Stats', onclose, children: body })
    return { onclose, user: userEvent.setup() }
}

describe('Modal', () => {
    test('renders nothing while closed', () => {
        renderModal(false)
        expect(screen.queryByRole('dialog')).toBeNull()
    })

    test('open: a labeled dialog with its content', () => {
        renderModal(true)
        const dialog = screen.getByRole('dialog', { name: 'Stats' })
        expect(dialog.textContent).toContain('Modal body')
    })

    test('the close button closes it', async () => {
        const { onclose, user } = renderModal(true)
        await user.click(screen.getByRole('button', { name: 'Close' }))
        expect(onclose).toHaveBeenCalledTimes(1)
    })

    test('Escape closes it', async () => {
        const { onclose, user } = renderModal(true)
        await user.keyboard('{Escape}')
        expect(onclose).toHaveBeenCalledTimes(1)
    })
})
