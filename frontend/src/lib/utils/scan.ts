/** Clamp to a valid transaction quantity: at least 1, rounded to integer. */
export function clampQuantity(value: number): number {
    if (!Number.isFinite(value)) {
        return 1
    }
    return Math.max(1, Math.round(value))
}

export function parseLookupCategory(raw: string | null | undefined): string | null {
    if (!raw) {
        return null
    }
    const parts = raw
        .split(',')
        .map((p) => p.trim())
        .filter(Boolean)
        .map((p) => p.replace(/^[a-z]{2}:/i, ''))
        .filter(Boolean)

    if (parts.length === 0) {
        return null
    }

    const candidate = parts[parts.length - 1].trim()
    if (!candidate) {
        return null
    }

    return candidate.charAt(0).toUpperCase() + candidate.slice(1)
}
