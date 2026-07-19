import type { Category, Product } from '$lib/api/client'
import { resolveIcon } from '$lib/utils/category'

/** Max emoji shown per product. Beyond this the pile saturates, so a single
 *  consume from a huge stock doesn't visibly change anything — and for
 *  stock <= cap, one consume removes exactly one dot. */
export const DOT_CAP = 8

/** A single placed emoji in the chamber scene. `key` is stable across stock
 *  changes so a keyed {#each} can animate one dot out without reflowing its
 *  siblings — the foundation tap-to-consume (WL-5.2) hangs off. */
export interface ChamberDot {
    key: string
    productId: number
    slot: number
    productName: string
    emoji: string
    isUrl: boolean
    src: string
    x: number // absolute % of scene width
    y: number // absolute % of scene height
    z: number // z-index
    title: string
}

/** Slots the caller has locally consumed (tapped) but not yet reconciled with a
 *  server reload, keyed by product id. Lets the exact tapped dot vanish. */
export type ConsumedSlots = Map<number, number[]>

export function isUrl(str: string): boolean {
    return str.startsWith('http') || str.startsWith('data:')
}

/** Which dot slots to draw for a product, given its server stock and the slots
 *  locally consumed since the last reload.
 *
 *  Slots are stable positions (seeded on `(product, slot)`); we render the first
 *  `effectiveStock` un-consumed slots, capped at DOT_CAP. Two consequences:
 *  - the *tapped* slot is the one that disappears (it's excluded), so the dot
 *    you touch is the dot that poofs — not some other one;
 *  - a big pile (stock > cap) refills from the reserve (slot 8, 9, …) as low
 *    slots are consumed, so it stays full instead of growing phantom holes. */
export function visibleSlots(
    stock: number,
    consumed: readonly number[] = [],
): number[] {
    const consumedSet = new Set(consumed)
    const effectiveStock = Math.max(0, Math.floor(stock)) - consumedSet.size
    const target = Math.min(Math.max(0, effectiveStock), DOT_CAP)
    const slots: number[] = []
    for (let slot = 0; slots.length < target; slot++) {
        if (!consumedSet.has(slot)) {
            slots.push(slot)
        }
    }
    return slots
}

// --- Deterministic placement -------------------------------------------------

// djb2-style hash → unsigned 32-bit
function hash(str: string): number {
    let acc = 5381
    for (let i = 0; i < str.length; i++) {
        acc = (((acc << 5) + acc) ^ str.charCodeAt(i)) >>> 0
    }
    return acc
}

// Seeded PRNG (mulberry32): deterministic placement that's stable across
// reloads, with enough variance that dots don't collapse onto each other.
function mulberry32(seed: number): () => number {
    let state = seed >>> 0
    return () => {
        state += 0x6d2b79f5
        let x = Math.imul(state ^ (state >>> 15), 1 | state)
        x ^= x + Math.imul(x ^ (x >>> 7), 61 | x)
        return ((x ^ (x >>> 14)) >>> 0) / 4294967296
    }
}

// Box-Muller: one seed → a standard-normal pair, for well-spread scatter.
function randomNormalPair(seed: number): [number, number] {
    const rand = mulberry32(seed)
    const u1 = Math.max(rand(), 1e-12)
    const u2 = rand()
    const radius = Math.sqrt(-2 * Math.log(u1))
    return [radius * Math.cos(2 * Math.PI * u2), radius * Math.sin(2 * Math.PI * u2)]
}

function clamp(value: number, lo: number, hi: number): number {
    return Math.max(lo, Math.min(hi, value))
}

// Unnormalized Gaussian bell, used only as a relative "lift" (center higher,
// edges lower), so no normalization constant is needed.
function normalPdf(x: number, mu: number, sigma: number): number {
    const z = (x - mu) / sigma
    return Math.exp(-0.5 * z * z)
}

const EMOJI_RULES: [RegExp, string][] = [
    [/milk|milch|lait|vollmilch|skimmed|dairy|molkerei/, '🥛'],
    [/egg|ei\b|eier|oeuf/, '🥚'],
    [/bread|brot|pain|toast|baguette|brötchen/, '🍞'],
    [/cheese|käse|fromage/, '🧀'],
    [/butter/, '🧈'],
    [/yogu?rt|joghurt/, '🫙'],
    [/cream|sahne|crème/, '🍦'],
    [/apple|apfel|pomme/, '🍎'],
    [/banana|banane/, '🍌'],
    [/orange/, '🍊'],
    [/lemon|zitrone|citron/, '🍋'],
    [/strawberr|erdbeere/, '🍓'],
    [/cherry|kirsche|cerise/, '🍒'],
    [/grape|traube|weintraube|raisin/, '🍇'],
    [/pineapple|ananas/, '🍍'],
    [/mango/, '🥭'],
    [/avocado/, '🥑'],
    [/peach|pfirsich|pêche/, '🍑'],
    [/pear|birne|poire/, '🍐'],
    [/melon|melone/, '🍈'],
    [/kiwi/, '🥝'],
    [/tomato|tomate/, '🍅'],
    [/carrot|karotte|möhre|rübe/, '🥕'],
    [/potato|kartoffel|pommes/, '🥔'],
    [/broccoli|brokkoli/, '🥦'],
    [/corn|mais/, '🌽'],
    [/cucumber|gurke|concombre/, '🥒'],
    [/pepper|paprika/, '🫑'],
    [/onion|zwiebel|oignon/, '🧅'],
    [/garlic|knoblauch|ail/, '🧄'],
    [/lettuce|kopfsalat|laitue/, '🥬'],
    [/mushroom|pilz|champignon/, '🍄'],
    [/eggplant|aubergine/, '🍆'],
    [/chicken|hähnchen|poulet|hühn/, '🍗'],
    [/ham|schinken|jambon/, '🍖'],
    [/sausage|wurst|bratwurst|salami|würst/, '🌭'],
    [/beef|steak|rind|fleisch|meat|viande/, '🥩'],
    [/fish|fisch|lachs|salmon|thun|tuna|forelle|trout/, '🐟'],
    [/shrimp|garnele|prawn|crevette/, '🦐'],
    [/coffee|kaffee|espresso|cappuccino|latte/, '☕'],
    [/tea|tee|thé/, '🍵'],
    [/juice|saft|jus/, '🧃'],
    [/water|wasser|eau/, '💧'],
    [/beer|bier|bière/, '🍺'],
    [/wine|wein|vin/, '🍷'],
    [/cola|soda|limo|limonade|softdrink/, '🥤'],
    [/chocolate|schokolade|kakao|chocolat/, '🍫'],
    [/pasta|nudel|spaghetti|penne|fusilli|tagliatelle/, '🍝'],
    [/rice|reis|riz/, '🍚'],
    [/pizza/, '🍕'],
    [/burger/, '🍔'],
    [/cereal|müsli|muesli|granola|haferflocken|oat/, '🥣'],
    [/oil|öl|olive|huile/, '🫒'],
    [/salt|salz|sel/, '🧂'],
    [/sugar|zucker|sucre/, '🍬'],
    [/honey|honig|miel/, '🍯'],
    [/jam|marmelade|confiture/, '🫙'],
    [/sauce|ketchup|mustard|senf/, '🥫'],
    [/soup|suppe|bouillon/, '🍲'],
    [/nut|nuss|peanut|cashew|almond|mandel|haselnuss/, '🥜'],
    [/cookie|keks|biscuit/, '🍪'],
    [/cake|torte|kuchen/, '🎂'],
    [/chip|crisp|snack|cracker/, '🥨'],
    [/bean|bohne/, '🫘'],
    [/pea|erbse/, '🫛'],
    [/tofu/, '🧆'],
    [/frozen|tiefkühl|surgelé/, '🧊'],
]

/** Best-guess emoji from a product's name + category, falling back to 📦. */
export function emojiFor(name: string, category: string | null): string {
    const haystack = [name, category ?? ''].join(' ').toLowerCase()
    for (const [pattern, emoji] of EMOJI_RULES) {
        if (pattern.test(haystack)) {
            return emoji
        }
    }
    return '📦'
}

interface ResolvedIcon {
    emoji: string
    isUrl: boolean
    src: string
}

function iconFor(product: Product, allCategories: Category[]): ResolvedIcon {
    const catIcon = resolveIcon(product.category, allCategories)
    if (catIcon && isUrl(catIcon)) {
        return { emoji: '', isUrl: true, src: catIcon }
    }
    return {
        emoji: catIcon ?? emojiFor(product.name, product.category?.name ?? null),
        isUrl: false,
        src: '',
    }
}

// Group products by category name, ordered by a STABLE key (the name), not by
// live stock. Sorting by stock would let a single consume tip two near-equal
// categories' order and slide both piles sideways — the reflow we're avoiding.
function groupByCategory(products: Product[]): [string, Product[]][] {
    const map = new Map<string, Product[]>()
    for (const product of products) {
        const key = product.category?.name ?? '?'
        const bucket = map.get(key)
        if (bucket) {
            bucket.push(product)
        } else {
            map.set(key, [product])
        }
    }
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]))
}

// One category's dots: a Gaussian blob sitting on the chamber floor, centered
// on an S-curve so categories cluster near the middle with thinner tails.
function buildPile(
    items: Product[],
    catIndex: number,
    catCount: number,
    allCategories: Category[],
    consumed: ConsumedSlots,
): ChamberDot[] {
    const dots: ChamberDot[] = []

    // x/y are percentages of the scene. Keep a small inner padding so big
    // emojis don't clip the edges.
    const safeLeft = 5
    const safeRight = 95
    const unit = (catIndex + 0.5) / Math.max(1, catCount)
    const centered = (unit - 0.5) * 2 // -1..1
    const gaussLike = centered / Math.sqrt(1 + 0.6 * centered * centered) // soft S
    const cx = safeLeft + ((gaussLike + 1) / 2) * (safeRight - safeLeft)
    const floorY = 85

    for (const product of items) {
        const { emoji, isUrl: urlIcon, src } = iconFor(product, allCategories)
        const consumedHere = consumed.get(product.id) ?? []
        const effectiveStock = Math.max(
            0,
            Math.floor(product.stock) - consumedHere.length,
        )

        for (const slot of visibleSlots(product.stock, consumedHere)) {
            // Seed on (product, slot) only — NOT on count — so a dot's position
            // is fixed regardless of how many siblings exist. That's what lets
            // one consume remove exactly one dot with the rest staying put.
            const [gx, gy] = randomNormalPair(hash(`${product.id}:${slot}`))
            const x = clamp(cx + gx * 12.5, safeLeft, safeRight)
            // centerLift raises dots near the pile center; gy adds depth jitter.
            const centerLift = normalPdf(x, cx, 10.5) * 11.5
            const y = clamp(floorY - centerLift + gy * 4.6, 60, floorY)

            dots.push({
                key: `${product.id}:${slot}`,
                productId: product.id,
                slot,
                productName: product.name,
                emoji,
                isUrl: urlIcon,
                src,
                x,
                y,
                z: 0,
                title: `${product.name} ×${effectiveStock}`,
            })
        }
    }

    // Painter's order: dots closer to the floor (larger y) render in front.
    for (const dot of dots) {
        dot.z = Math.round((dot.y - 50) * 0.8) + catIndex
    }
    return dots
}

/** Flatten all products into positioned, stably-keyed chamber dots. `consumed`
 *  overlays locally-tapped slots so the exact dots tapped are the ones gone. */
export function buildDots(
    products: Product[],
    allCategories: Category[],
    consumed: ConsumedSlots = new Map(),
): ChamberDot[] {
    const groups = groupByCategory(products)
    return groups.flatMap((entry, index) =>
        buildPile(entry[1], index, groups.length, allCategories, consumed),
    )
}
