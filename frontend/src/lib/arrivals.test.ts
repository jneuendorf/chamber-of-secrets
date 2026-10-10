import { expect, test } from 'bun:test'

import { cancelArrival, drainArrivals, queueArrival } from './arrivals'

test('drain sums per product, honors cancels, and empties the queue', () => {
    queueArrival(1, 10, 2)
    queueArrival(2, 10, 1)
    queueArrival(3, 20, 4)
    cancelArrival(3)
    expect(drainArrivals()).toEqual(new Map([[10, 3]]))
    expect(drainArrivals().size).toBe(0)
})
