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

// Digit counts of the GS1 symbologies the scanner reads (BarcodeScanner.svelte
// formats: ean_8 = 8, upc_e = 6 or 8, upc_a = 12, ean_13 = 13). Anything else
// is a typo or an Open Food Facts placeholder entry (e.g. "1234"), so we skip
// the lookup and route straight to manual entry.
const BARCODE_LENGTHS = new Set([6, 8, 12, 13])

/** True when `code` is all digits and a valid retail barcode length. */
export function isPlausibleBarcode(code: string): boolean {
    return /^\d+$/.test(code) && BARCODE_LENGTHS.has(code.length)
}

interface ProductDraft {
    ean: string
    name: string | null
    brand: string | null
    image_url: string | null
}

/**
 * Normalise a scanned or manually-entered draft into a product-create payload:
 * blank EAN → null (so manual products don't collide), whitespace trimmed,
 * empty optional fields → null, missing name → fallback (WL-4.1).
 */
export function buildProductPayload(
    draft: ProductDraft,
    fallbackName: string,
    categoryId: number | null,
) {
    return {
        ean: draft.ean || null,
        name: draft.name?.trim() || fallbackName,
        brand: draft.brand?.trim() || null,
        image_url: draft.image_url?.trim() || null,
        category_id: categoryId,
    }
}
