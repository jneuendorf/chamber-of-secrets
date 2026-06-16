import { describe, expect, test } from 'bun:test'

import de from './de.json'
import en from './en.json'

type LocaleObject = Record<string, unknown>

function collectKeys(obj: LocaleObject, prefix = ''): string[] {
    const keys: string[] = []
    for (const key of Object.keys(obj)) {
        const full = prefix ? `${prefix}.${key}` : key
        const val = obj[key]
        if (val !== null && typeof val === 'object' && !Array.isArray(val)) {
            keys.push(...collectKeys(val as LocaleObject, full))
        } else {
            keys.push(full)
        }
    }
    return keys.sort()
}

function resolve(obj: LocaleObject, path: string): unknown {
    return path.split('.').reduce<unknown>((o, p) => {
        if (o !== null && typeof o === 'object') {
            return (o as LocaleObject)[p]
        }
        return undefined
    }, obj)
}

describe('i18n locale sync', () => {
    const enKeys = collectKeys(en)
    const deKeys = collectKeys(de)

    test('EN and DE have identical key sets', () => {
        const missingInDE = enKeys.filter((k) => !deKeys.includes(k))
        const missingInEN = deKeys.filter((k) => !enKeys.includes(k))

        if (missingInDE.length > 0 || missingInEN.length > 0) {
            const parts: string[] = []
            if (missingInDE.length > 0) {
                parts.push(`Missing in DE: ${missingInDE.join(', ')}`)
            }
            if (missingInEN.length > 0) {
                parts.push(`Missing in EN: ${missingInEN.join(', ')}`)
            }
            throw new Error(`Locale key mismatch.\n${parts.join('\n')}`)
        }
    })

    test('no empty string values in EN', () => {
        const empty = enKeys.filter((k) => resolve(en, k) === '')
        expect(empty).toEqual([])
    })

    test('no empty string values in DE', () => {
        const empty = deKeys.filter((k) => resolve(de, k) === '')
        expect(empty).toEqual([])
    })
})
