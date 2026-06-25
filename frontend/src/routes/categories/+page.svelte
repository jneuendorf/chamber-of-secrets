<script lang="ts">
    import { get } from 'svelte/store'
    import { _ } from 'svelte-i18n'

    import { ApiError, api, type Category } from '$lib/api/client'
    import FuzzySearchOverlay from '$lib/components/FuzzySearchOverlay.svelte'
    import Modal from '$lib/components/Modal.svelte'
    import Select from '$lib/components/Select.svelte'
    import { resolveIcon } from '$lib/utils/category'

    type CategoryForm = {
        name: string
        icon: string
        parent_id: number | null
        restock_target_input: string
        restock_min_input: string
        restock_inherit: boolean
    }

    type EffectivePreview = {
        target: number | null
        min: number | null
        targetFrom: number | null
        minFrom: number | null
    }

    const ROOT_PARENT = '__root__'

    let categories: Category[] = $state([])
    let loading = $state(true)
    let savingId: number | null = $state(null)
    let deletingId: number | null = $state(null)
    let error = $state('')
    let searchOpen = $state(false)

    let navStack: { id: number; name: string }[] = $state([])
    let direction: 'forward' | 'back' = $state('forward')
    let navLevel = $derived(navStack.length)
    let currentParentId: number | null = $derived(
        navStack.length > 0 ? navStack[navStack.length - 1].id : null,
    )
    let currentCategories = $derived(
        categories
            .filter((cat) => (cat.parent_id ?? null) === currentParentId)
            .sort((catA, catB) => catA.name.localeCompare(catB.name)),
    )

    let newCategoryName = $state('')
    let newCategoryParentId = $state<number | null>(null)
    let creatingCategory = $state(false)

    let expanded = $state<Set<number>>(new Set())

    const forms = new Map<number, CategoryForm>()

    function selectCategoryFromSearch(item: unknown) {
        const category = item as Category
        const byId = categoryByIdMap()

        const path: { id: number; name: string }[] = []
        let cur = category.parent_id != null ? byId.get(category.parent_id) : undefined
        while (cur) {
            path.unshift({ id: cur.id, name: cur.name })
            if (cur.parent_id == null) {
                break
            }
            cur = byId.get(cur.parent_id)
        }

        direction = 'forward'
        navStack = path
        newCategoryParentId = path.length > 0 ? path[path.length - 1].id : null

        const copy = new Set(expanded)
        copy.add(category.id)
        expanded = copy

        requestAnimationFrame(() => {
            document
                .querySelector(`[data-category-id="${category.id}"]`)
                ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
        })
    }

    async function load() {
        loading = true
        error = ''
        try {
            categories = await api.categories.list()
            forms.clear()
            for (const c of categories) {
                forms.set(c.id, {
                    name: c.name,
                    icon: c.icon ?? '',
                    parent_id: c.parent_id,
                    restock_target_input:
                        c.restock_target === null || c.restock_target === undefined
                            ? ''
                            : String(c.restock_target),
                    restock_min_input:
                        c.restock_min === null || c.restock_min === undefined
                            ? ''
                            : String(c.restock_min),
                    restock_inherit: c.restock_inherit ?? true,
                })
            }
            expanded = new Set() // all collapsed by default
        } catch (e) {
            const detail = e instanceof ApiError ? e.detail : String(e)
            error = get(_)('inventory.failedToLoad', { values: { error: detail } })
        } finally {
            loading = false
        }
    }

    $effect(() => {
        load()
    })

    function categoryByIdMap() {
        return new Map(categories.map((c) => [c.id, c]))
    }

    function childrenByParentMap() {
        const m = new Map<number | null, Category[]>()
        for (const c of categories) {
            const key = c.parent_id ?? null
            if (!m.has(key)) {
                m.set(key, [])
            }
            m.get(key)!.push(c)
        }
        for (const arr of m.values()) {
            arr.sort((a, b) => a.name.localeCompare(b.name))
        }
        return m
    }

    function isDescendant(candidateChildId: number, ancestorId: number): boolean {
        const byId = categoryByIdMap()
        let cur = byId.get(candidateChildId) ?? null
        const seen = new Set<number>()
        while (cur && cur.parent_id != null) {
            if (seen.has(cur.id)) {
                break
            }
            seen.add(cur.id)
            if (cur.parent_id === ancestorId) {
                return true
            }
            cur = byId.get(cur.parent_id) ?? null
        }
        return false
    }

    function parentOptionsFor(category: Category): Category[] {
        return categories
            .filter((c) => c.id !== category.id && !isDescendant(c.id, category.id))
            .sort((a, b) => a.name.localeCompare(b.name))
    }

    function parseNullableFloat(input: string | number): number | null {
        if (typeof input === 'number') {
            return Number.isFinite(input) ? input : NaN
        }
        const trimmed = input.trim()
        if (!trimmed) {
            return null
        }
        const n = Number(trimmed)
        return Number.isFinite(n) ? n : NaN
    }

    function computeEffectivePreview(categoryId: number): EffectivePreview {
        const byId = categoryByIdMap()
        const start = byId.get(categoryId)
        if (!start) {
            return { target: null, min: null, targetFrom: null, minFrom: null }
        }

        const resolveOne = (
            field: 'restock_target' | 'restock_min',
        ): [number | null, number | null] => {
            const visited = new Set<number>()
            let cur: Category | undefined = start
            while (cur) {
                if (visited.has(cur.id)) {
                    return [null, null]
                }
                visited.add(cur.id)

                const form = forms.get(cur.id)
                const value =
                    field === 'restock_target'
                        ? parseNullableFloat(form?.restock_target_input ?? '')
                        : parseNullableFloat(form?.restock_min_input ?? '')

                if (value !== null && !Number.isNaN(value)) {
                    return [value, cur.id]
                }
                if (
                    !(form?.restock_inherit ?? cur.restock_inherit ?? true) ||
                    cur.parent_id == null
                ) {
                    return [null, null]
                }
                cur = byId.get(cur.parent_id)
            }
            return [null, null]
        }

        const [target, targetFrom] = resolveOne('restock_target')
        const [min, minFrom] = resolveOne('restock_min')
        return { target, min, targetFrom, minFrom }
    }

    function sourceLabel(sourceId: number | null): string {
        if (sourceId == null) {
            return get(_)('common.unknown')
        }
        const cat = categories.find((c) => c.id === sourceId)
        return cat ? cat.name : `#${sourceId}`
    }

    function toggleExpand(id: number) {
        const copy = new Set(expanded)
        if (copy.has(id)) {
            copy.delete(id)
        } else {
            copy.add(id)
        }
        expanded = copy
    }

    function drillIn(cat: Category) {
        direction = 'forward'
        navStack = [...navStack, { id: cat.id, name: cat.name }]
        newCategoryParentId = cat.id
    }

    function goBack() {
        direction = 'back'
        navStack = navStack.slice(0, -1)
        newCategoryParentId =
            navStack.length > 0 ? navStack[navStack.length - 1].id : null
    }

    function validateForm(cat: Category, form: CategoryForm): string | null {
        const target = parseNullableFloat(form.restock_target_input)
        const min = parseNullableFloat(form.restock_min_input)

        if (Number.isNaN(target) || Number.isNaN(min)) {
            return get(_)('category.validationInvalidNumbers')
        }
        if ((target ?? 0) < 0 || (min ?? 0) < 0) {
            return get(_)('category.validationNonNegative')
        }
        if (target !== null && min !== null && target < min) {
            return get(_)('category.validationTargetGteMin')
        }
        if (!form.name.trim()) {
            return get(_)('category.validationNameRequired')
        }
        if (form.parent_id === cat.id) {
            return get(_)('category.validationSelfParent')
        }
        return null
    }

    async function saveCategory(cat: Category) {
        const form = forms.get(cat.id)
        if (!form) {
            return
        }

        const msg = validateForm(cat, form)
        if (msg) {
            error = msg
            return
        }

        error = ''
        savingId = cat.id
        try {
            const payload = {
                name: form.name.trim(),
                icon: form.icon.trim() || null,
                parent_id: form.parent_id,
                restock_target: parseNullableFloat(form.restock_target_input),
                restock_min: parseNullableFloat(form.restock_min_input),
                restock_inherit: form.restock_inherit,
            }
            const updated = await api.categories.update(cat.id, payload)
            categories = categories.map((c) => (c.id === updated.id ? updated : c))
            forms.set(updated.id, {
                name: updated.name,
                icon: updated.icon ?? '',
                parent_id: updated.parent_id,
                restock_target_input:
                    updated.restock_target === null
                        ? ''
                        : String(updated.restock_target),
                restock_min_input:
                    updated.restock_min === null ? '' : String(updated.restock_min),
                restock_inherit: updated.restock_inherit,
            })
        } catch (e) {
            const detail = e instanceof ApiError ? e.detail : String(e)
            error = get(_)('category.failedToSave', { values: { error: detail } })
        } finally {
            savingId = null
        }
    }

    async function createCategory() {
        const name = newCategoryName.trim()
        if (!name) {
            return
        }
        creatingCategory = true
        error = ''
        try {
            const created = await api.categories.create({
                name,
                parent_id: newCategoryParentId,
            })
            categories = [...categories, created]
            forms.set(created.id, {
                name: created.name,
                icon: created.icon ?? '',
                parent_id: created.parent_id,
                restock_target_input: '',
                restock_min_input: '',
                restock_inherit: created.restock_inherit ?? true,
            })
            newCategoryName = ''
            newCategoryParentId = null
            const copy = new Set(expanded)
            copy.add(created.id)
            expanded = copy
        } catch (e) {
            const detail = e instanceof ApiError ? e.detail : String(e)
            error = get(_)('category.failedToSave', { values: { error: detail } })
        } finally {
            creatingCategory = false
        }
    }

    let confirmingDelete: Category | null = $state(null)

    async function confirmDelete() {
        if (!confirmingDelete) {
            return
        }
        const cat = confirmingDelete
        confirmingDelete = null
        deletingId = cat.id
        error = ''
        try {
            await api.categories.delete(cat.id)
            categories = categories.filter((c) => c.id !== cat.id)
            forms.delete(cat.id)
            const copy = new Set(expanded)
            copy.delete(cat.id)
            expanded = copy
            const stackIdx = navStack.findIndex((entry) => entry.id === cat.id)
            if (stackIdx >= 0) {
                navStack = navStack.slice(0, stackIdx)
                newCategoryParentId =
                    navStack.length > 0 ? navStack[navStack.length - 1].id : null
            }
        } catch (e) {
            const detail = e instanceof ApiError ? e.detail : String(e)
            error = get(_)('category.failedToDelete', { values: { error: detail } })
        } finally {
            deletingId = null
        }
    }

    function childrenOf(parentId: number) {
        return childrenByParentMap().get(parentId) ?? []
    }
</script>

<div class="flex items-center justify-between gap-3 mt-0 mb-1">
    <h1 class="m-0">{$_('category.managementTitle')} ({categories.length})</h1>
    <button
        type="button"
        class="search-indicator"
        aria-label={$_('category.searchHint')}
        title={$_('category.searchHint')}
        onclick={() => (searchOpen = true)}
    >
        ⌕ {$_('common.searchIndicator')}
    </button>
</div>
<p class="text-gray-500 mt-1 mb-5">
    {$_('category.managementSubtitle')}
</p>

{#if !loading}
    <form
        class="create-form"
        onsubmit={(e) => {
            e.preventDefault()
            createCategory()
        }}
    >
        <input
            type="text"
            bind:value={newCategoryName}
            placeholder={$_('category.newPlaceholder')}
            disabled={creatingCategory}
            class="flex-1 px-3 py-2 border border-bark-600 bg-bark-850 text-gray-100 rounded-lg text-sm"
        />
        <Select
            class="px-3 py-2 border border-bark-600 bg-bark-850 text-gray-100 rounded-lg text-sm"
            disabled={creatingCategory}
            value={newCategoryParentId ?? ROOT_PARENT}
            onchange={(val) => {
                newCategoryParentId = val === ROOT_PARENT ? null : Number(val)
            }}
            items={[
                { value: ROOT_PARENT, label: $_('category.noParent') },
                ...categories
                    .toSorted((catA, catB) => catA.name.localeCompare(catB.name))
                    .map((cat) => ({
                        value: cat.id,
                        label: cat.name,
                        icon: resolveIcon(cat, categories),
                    })),
            ]}
        />
        <button
            type="submit"
            disabled={!newCategoryName.trim() || creatingCategory}
            class="px-4 py-2 bg-accent-900 text-white rounded-lg text-sm font-medium disabled:opacity-40 shrink-0"
        >
            {$_('category.add')}
        </button>
    </form>

    {#if navStack.length > 0}
        <nav class="drill-header">
            <button type="button" class="drill-back" onclick={goBack}>‹</button>
            <span class="drill-title">{navStack[navStack.length - 1].name}</span>
        </nav>
    {/if}
{/if}

{#if loading}
    <p>{$_('common.loading')}</p>
{/if}

{#if error}
    <p class="text-danger-500">{error}</p>
{/if}

{#if !loading && categories.length === 0}
    <p class="text-center text-gray-500 my-10">
        {$_('category.emptyManagement')}
    </p>
{:else if !loading}
    <FuzzySearchOverlay
        items={categories}
        keys={['name', 'icon']}
        getId={(item) => (item as Category).id}
        getLabel={(item) => (item as Category).name}
        getSecondaryLabel={(item) => {
            const c = item as Category
            if (c.parent_id == null) {
                return $_('category.noParent')
            }
            const parent = categories.find((p) => p.id === c.parent_id)
            return parent ? parent.name : $_('common.unknown')
        }}
        onSelect={selectCategoryFromSearch}
        placeholder={$_('category.searchPlaceholder')}
        noResultsText={$_('category.searchNoResults')}
        hintText={$_('category.searchHint')}
        bind:open={searchOpen}
    />

    {#key navLevel}
        <div
            class="drill-panel"
            class:slide-right={direction === 'forward' && navLevel > 0}
            class:slide-left={direction === 'back'}
        >
            {#if currentCategories.length === 0}
                <p class="text-center text-gray-500 my-10">
                    {$_('category.emptyLevel')}
                </p>
            {:else}
                <div class="category-list">
                    {#each currentCategories as cat (cat.id)}
                        {@const form = forms.get(cat.id)!}
                        {@const eff = computeEffectivePreview(cat.id)}
                        {@const icon = resolveIcon(cat, categories)}
                        {@const childCount = childrenOf(cat.id).length}
                        <section class="node-card" data-category-id={cat.id}>
                            <header class="node-head">
                                <button
                                    type="button"
                                    class="collapse-btn"
                                    class:expanded={expanded.has(cat.id)}
                                    onclick={() => toggleExpand(cat.id)}
                                    title={expanded.has(cat.id)
                                        ? $_('category.collapse')
                                        : $_('category.expand')}
                                >
                                    ›
                                </button>
                                {#if childCount > 0}
                                    <button
                                        type="button"
                                        class="drill-area"
                                        onclick={() => drillIn(cat)}
                                    >
                                        {#if icon}<span class="node-icon">{icon}</span
                                            >{/if}
                                        <strong>{cat.name}</strong>
                                        <span class="child-badge">
                                            {childCount} ›
                                        </span>
                                    </button>
                                {:else}
                                    {#if icon}<span class="node-icon">{icon}</span>{/if}
                                    <strong>{cat.name}</strong>
                                {/if}
                                <span class="pill"
                                    >{$_('category.idLabel', {
                                        values: { id: cat.id },
                                    })}</span
                                >
                            </header>

                            {#if expanded.has(cat.id)}
                                <div class="grid">
                                    <label>
                                        {$_('category.nameLabel')}
                                        <input bind:value={form.name} />
                                    </label>
                                    <label>
                                        {$_('category.editIcon')}
                                        <input
                                            bind:value={form.icon}
                                            placeholder={$_('category.iconPlaceholder')}
                                        />
                                    </label>
                                    <label>
                                        {$_('category.parentLabel')}
                                        <Select
                                            value={form.parent_id ?? ROOT_PARENT}
                                            onchange={(val) => {
                                                form.parent_id =
                                                    val === ROOT_PARENT
                                                        ? null
                                                        : Number(val)
                                            }}
                                            items={[
                                                {
                                                    value: ROOT_PARENT,
                                                    label: $_('category.noParent'),
                                                },
                                                ...parentOptionsFor(cat).map((opt) => ({
                                                    value: opt.id,
                                                    label: opt.name,
                                                    icon: resolveIcon(opt, categories),
                                                })),
                                            ]}
                                        />
                                    </label>
                                    <label class="toggle">
                                        <input
                                            type="checkbox"
                                            bind:checked={form.restock_inherit}
                                        />
                                        {$_('category.inheritLabel')}
                                    </label>
                                    <label>
                                        {$_('category.restockTargetLabel')}
                                        <input
                                            type="number"
                                            min="0"
                                            step="0.01"
                                            bind:value={form.restock_target_input}
                                        />
                                    </label>
                                    <label>
                                        {$_('category.restockMinLabel')}
                                        <input
                                            type="number"
                                            min="0"
                                            step="0.01"
                                            bind:value={form.restock_min_input}
                                        />
                                    </label>
                                </div>

                                <div class="effective">
                                    <div>
                                        <strong
                                            >{$_('category.effectiveTarget')}:</strong
                                        >
                                        {eff.target ?? $_('category.unset')}
                                    </div>
                                    <div>
                                        <strong>{$_('category.effectiveMin')}:</strong>
                                        {eff.min ?? $_('category.unset')}
                                    </div>
                                    <div class="muted">
                                        {$_('category.sourceTarget', {
                                            values: {
                                                name: sourceLabel(eff.targetFrom),
                                            },
                                        })} ·
                                        {$_('category.sourceMin', {
                                            values: { name: sourceLabel(eff.minFrom) },
                                        })}
                                    </div>
                                </div>

                                <div class="actions">
                                    <button
                                        type="button"
                                        class="delete"
                                        disabled={deletingId === cat.id}
                                        onclick={() => (confirmingDelete = cat)}
                                    >
                                        {$_('category.deleteButton')}
                                    </button>
                                    <button
                                        type="button"
                                        class="save"
                                        disabled={savingId === cat.id}
                                        onclick={() => saveCategory(cat)}
                                    >
                                        {savingId === cat.id
                                            ? $_('category.saving')
                                            : $_('category.saveButton')}
                                    </button>
                                </div>
                            {/if}
                        </section>
                    {/each}
                </div>
            {/if}
        </div>
    {/key}
{/if}

<Modal
    open={confirmingDelete !== null}
    title={$_('category.deleteConfirm', {
        values: { name: confirmingDelete?.name ?? '' },
    })}
    onclose={() => (confirmingDelete = null)}
>
    <div class="confirm-actions">
        <button
            type="button"
            class="confirm-cancel"
            onclick={() => (confirmingDelete = null)}
        >
            {$_('common.cancel')}
        </button>
        <button type="button" class="confirm-delete" onclick={confirmDelete}>
            {$_('category.deleteButton')}
        </button>
    </div>
</Modal>

<style>
    .confirm-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
        margin-top: 0.5rem;
    }

    .confirm-cancel {
        background: var(--color-bark-850);
        color: var(--color-ink-200);
        border: 1px solid var(--color-bark-600);
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
        font-weight: 600;
        cursor: pointer;
    }

    .confirm-cancel:hover {
        background: var(--color-bark-730);
    }

    .confirm-delete {
        background: var(--color-danger-900);
        color: var(--color-danger-200);
        border: 1px solid var(--color-danger-800);
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
        font-weight: 600;
        cursor: pointer;
    }

    .confirm-delete:hover {
        background: var(--color-danger-800);
    }

    .drill-header {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        margin-bottom: 0.75rem;
    }

    .drill-back {
        background: none;
        border: none;
        color: var(--color-info-500);
        font-size: 1.4rem;
        font-weight: 600;
        cursor: pointer;
        padding: 0 0.2rem;
        line-height: 1;
    }

    .drill-back:hover {
        color: var(--color-info-400);
    }

    .drill-title {
        font-size: 1rem;
        font-weight: 600;
        color: var(--color-ink-200);
    }

    .drill-panel {
        overflow: hidden;
    }

    .slide-right {
        animation: slideRight 0.28s ease-out;
    }

    .slide-left {
        animation: slideLeft 0.28s ease-out;
    }

    @keyframes slideRight {
        from {
            transform: translateX(40%);
            opacity: 0.15;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideLeft {
        from {
            transform: translateX(-40%);
            opacity: 0.15;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    .category-list {
        display: grid;
        gap: 1rem;
    }

    .node-card {
        background: var(--color-bark-800);
        border: 1px solid var(--color-bark-600);
        border-radius: 12px;
        padding: 1rem;
    }

    .node-head {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.8rem;
    }

    .collapse-btn {
        width: 1.7rem;
        height: 1.7rem;
        border-radius: 0.4rem;
        border: 1px solid var(--color-ink-600);
        background: var(--color-ink-900);
        color: var(--color-ink-200);
        cursor: pointer;
        flex-shrink: 0;
        transition: transform 0.15s ease;
    }

    .collapse-btn.expanded {
        transform: rotate(90deg);
    }

    .drill-area {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex: 1;
        min-width: 0;
        background: none;
        border: none;
        color: inherit;
        font: inherit;
        cursor: pointer;
        padding: 0.25rem 0.4rem;
        border-radius: 0.4rem;
        text-align: left;
    }

    .drill-area:hover {
        background: rgba(255, 255, 255, 0.05);
    }

    .child-badge {
        margin-left: auto;
        font-size: 0.8rem;
        color: var(--color-info-500);
        font-weight: 600;
        white-space: nowrap;
    }

    .pill {
        margin-left: auto;
        font-size: 0.75rem;
        color: var(--color-ink-250);
        background: var(--color-ink-900);
        border: 1px solid var(--color-ink-700);
        border-radius: 999px;
        padding: 0.15rem 0.5rem;
        flex-shrink: 0;
    }

    .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 0.7rem;
    }

    label {
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
        font-size: 0.85rem;
        color: var(--color-ink-600);
    }

    input {
        border: 1px solid var(--color-ink-600);
        border-radius: 8px;
        padding: 0.5rem 0.6rem;
        font-size: 0.95rem;
        background: var(--color-ink-900);
        color: var(--color-ink-100);
    }

    .toggle {
        justify-content: center;
    }

    .toggle input {
        width: 1rem;
        height: 1rem;
    }

    .effective {
        margin-top: 0.75rem;
        padding: 0.6rem 0.75rem;
        border-radius: 8px;
        background: var(--color-ink-900);
        border: 1px solid var(--color-ink-700);
        color: var(--color-ink-200);
        font-size: 0.9rem;
    }

    .muted {
        color: var(--color-ink-400);
        font-size: 0.8rem;
        margin-top: 0.2rem;
    }

    .actions {
        margin-top: 0.7rem;
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
    }

    .save {
        background: var(--color-accent-900);
        color: white;
        border: 0;
        border-radius: 8px;
        padding: 0.45rem 0.9rem;
        font-weight: 600;
        cursor: pointer;
    }

    .save:disabled,
    .delete:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .delete {
        background: transparent;
        color: var(--color-danger-450);
        border: 1px solid var(--color-danger-900);
        border-radius: 8px;
        padding: 0.45rem 0.9rem;
        font-weight: 600;
        cursor: pointer;
    }

    .delete:hover:not(:disabled) {
        background: var(--color-danger-900);
        color: var(--color-danger-200);
    }

    .create-form {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-bottom: 1.25rem;
    }

    .node-icon {
        font-size: 1.1rem;
        line-height: 1;
    }

    .search-indicator {
        font-size: 0.78rem;
        color: var(--color-ink-250);
        background: var(--color-ink-900);
        border: 1px solid var(--color-ink-700);
        border-radius: 999px;
        padding: 0.2rem 0.55rem;
        white-space: nowrap;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
    }

    .search-indicator:hover {
        background: var(--color-bark-800);
        color: var(--color-ink-100);
        border-color: var(--color-bark-600);
    }

    .search-indicator:focus-visible {
        outline: 2px solid var(--color-accent-500);
        outline-offset: 2px;
    }
</style>
