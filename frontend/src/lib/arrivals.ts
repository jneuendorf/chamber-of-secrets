/**
 * Pending chamber arrivals (WL-5.6): `/scan` queues every stock-in it records,
 * `/chamber` drains the queue on load and lets those dots arc into their piles.
 *
 * Keyed by transaction id, so undoing a scan withdraws exactly its arrival.
 * Module state, not persisted: it only has to survive a client-side navigation.
 * ponytail: a full reload drops pending arrivals — they just show up at rest.
 */
const pending = new Map<number, { productId: number; quantity: number }>()

export function queueArrival(txnId: number, productId: number, quantity: number) {
    pending.set(txnId, { productId, quantity })
}

export function cancelArrival(txnId: number) {
    pending.delete(txnId)
}

/** Empty the queue, returning how many items arrived per product id. */
export function drainArrivals(): Map<number, number> {
    const perProduct = new Map<number, number>()
    for (const { productId, quantity } of pending.values()) {
        perProduct.set(productId, (perProduct.get(productId) ?? 0) + quantity)
    }
    pending.clear()
    return perProduct
}
