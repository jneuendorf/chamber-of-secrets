import { describe, expect, mock, test } from 'bun:test'

import { render, screen } from '@testing-library/svelte'
import userEvent from '@testing-library/user-event'

import Select from './Select.svelte'

const items = [
    { value: 1, label: 'Dairy', icon: '🥛' },
    { value: 2, label: 'Fruit', icon: '🍎' },
]

// Bits UI's trigger is a button that pops up a listbox.
const trigger = () => screen.getByRole('button')

function renderSelect(value?: number) {
    const onchange = mock((_value: number) => {})
    render(Select<number>, { items, value, onchange })
    return { onchange, user: userEvent.setup() }
}

describe('Select', () => {
    test('shows the selected item on the trigger', () => {
        renderSelect(2)
        expect(trigger().textContent).toContain('Fruit')
    })

    // Bits UI works in strings; the wrapper must hand back the typed value.
    test('picking an option reports its typed value', async () => {
        const { onchange, user } = renderSelect(1)
        await user.click(trigger())
        await user.click(await screen.findByRole('option', { name: /Fruit/ }))
        expect(onchange).toHaveBeenCalledWith(2)
        expect(trigger().textContent).toContain('Fruit')
    })

    test('keyboard: open, move, choose', async () => {
        const { onchange, user } = renderSelect(1)
        trigger().focus()
        await user.keyboard('{Enter}')
        await screen.findByRole('listbox')
        await user.keyboard('{ArrowDown}{Enter}')
        expect(onchange).toHaveBeenCalledWith(2)
    })

    // WL-3.5: Escape closes only the open dropdown, not a surrounding modal.
    test('Escape closes the listbox', async () => {
        const { user } = renderSelect(1)
        await user.click(trigger())
        await screen.findByRole('listbox')
        await user.keyboard('{Escape}')
        expect(screen.queryByRole('listbox')).toBeNull()
    })
})
