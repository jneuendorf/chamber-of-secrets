<script lang="ts">
    import { get } from "svelte/store";
    import { _ } from "svelte-i18n";
    import FuzzySearchOverlay from "$lib/components/FuzzySearchOverlay.svelte";
    import { api, type Category } from "$lib/api/client";

    type CategoryForm = {
        name: string;
        icon: string;
        parent_id: number | null;
        restock_target_input: string;
        restock_min_input: string;
        restock_inherit: boolean;
    };

    type EffectivePreview = {
        target: number | null;
        min: number | null;
        targetFrom: number | null;
        minFrom: number | null;
    };

    const ROOT_PARENT = "__root__";

    let categories: Category[] = $state([]);
    let loading = $state(true);
    let savingId: number | null = $state(null);
    let error = $state("");
    let searchOpen = $state(false);

    // individual collapse state for every card (root + child)
    let expanded = $state<Set<number>>(new Set());

    const forms = new Map<number, CategoryForm>();

    function selectCategoryFromSearch(item: unknown) {
        const category = item as Category;
        const chain: number[] = [];
        const byId = categoryByIdMap();
        let cur: Category | undefined = category;
        const seen = new Set<number>();

        while (cur && !seen.has(cur.id)) {
            seen.add(cur.id);
            chain.push(cur.id);
            if (cur.parent_id == null) break;
            cur = byId.get(cur.parent_id);
        }

        const copy = new Set(expanded);
        for (const id of chain) copy.add(id);
        expanded = copy;

        document
            .querySelector(`[data-category-id="${category.id}"]`)
            ?.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    async function load() {
        loading = true;
        error = "";
        try {
            categories = await api.categories.list();
            forms.clear();
            for (const c of categories) {
                forms.set(c.id, {
                    name: c.name,
                    icon: c.icon ?? "",
                    parent_id: c.parent_id,
                    restock_target_input:
                        c.restock_target === null || c.restock_target === undefined
                            ? ""
                            : String(c.restock_target),
                    restock_min_input:
                        c.restock_min === null || c.restock_min === undefined
                            ? ""
                            : String(c.restock_min),
                    restock_inherit: c.restock_inherit ?? true,
                });
            }
            expanded = new Set(); // all collapsed by default
        } catch (e) {
            error = get(_)("inventory.failedToLoad", { values: { error: String(e) } });
        } finally {
            loading = false;
        }
    }

    $effect(() => {
        load();
    });

    function categoryByIdMap() {
        return new Map(categories.map((c) => [c.id, c]));
    }

    function childrenByParentMap() {
        const m = new Map<number | null, Category[]>();
        for (const c of categories) {
            const key = c.parent_id ?? null;
            if (!m.has(key)) m.set(key, []);
            m.get(key)!.push(c);
        }
        for (const arr of m.values()) {
            arr.sort((a, b) => a.name.localeCompare(b.name));
        }
        return m;
    }

    function isDescendant(candidateChildId: number, ancestorId: number): boolean {
        const byId = categoryByIdMap();
        let cur = byId.get(candidateChildId) ?? null;
        const seen = new Set<number>();
        while (cur && cur.parent_id != null) {
            if (seen.has(cur.id)) break;
            seen.add(cur.id);
            if (cur.parent_id === ancestorId) return true;
            cur = byId.get(cur.parent_id) ?? null;
        }
        return false;
    }

    function parentOptionsFor(category: Category): Category[] {
        return categories
            .filter((c) => c.id !== category.id && !isDescendant(c.id, category.id))
            .sort((a, b) => a.name.localeCompare(b.name));
    }

    function parseNullableFloat(input: string): number | null {
        const trimmed = input.trim();
        if (!trimmed) return null;
        const n = Number(trimmed);
        return Number.isFinite(n) ? n : NaN;
    }

    function computeEffectivePreview(categoryId: number): EffectivePreview {
        const byId = categoryByIdMap();
        const start = byId.get(categoryId);
        if (!start) return { target: null, min: null, targetFrom: null, minFrom: null };

        const resolveOne = (
            field: "restock_target" | "restock_min",
        ): [number | null, number | null] => {
            const visited = new Set<number>();
            let cur: Category | undefined = start;
            while (cur) {
                if (visited.has(cur.id)) return [null, null];
                visited.add(cur.id);

                const form = forms.get(cur.id);
                const value =
                    field === "restock_target"
                        ? parseNullableFloat(form?.restock_target_input ?? "")
                        : parseNullableFloat(form?.restock_min_input ?? "");

                if (value !== null && !Number.isNaN(value)) return [value, cur.id];
                if (
                    !(form?.restock_inherit ?? cur.restock_inherit ?? true) ||
                    cur.parent_id == null
                ) {
                    return [null, null];
                }
                cur = byId.get(cur.parent_id);
            }
            return [null, null];
        };

        const [target, targetFrom] = resolveOne("restock_target");
        const [min, minFrom] = resolveOne("restock_min");
        return { target, min, targetFrom, minFrom };
    }

    function sourceLabel(sourceId: number | null): string {
        if (sourceId == null) return get(_)("common.unknown");
        const cat = categories.find((c) => c.id === sourceId);
        return cat ? cat.name : `#${sourceId}`;
    }

    function toggleExpand(id: number) {
        const copy = new Set(expanded);
        if (copy.has(id)) copy.delete(id);
        else copy.add(id);
        expanded = copy;
    }

    function validateForm(cat: Category, form: CategoryForm): string | null {
        const target = parseNullableFloat(form.restock_target_input);
        const min = parseNullableFloat(form.restock_min_input);

        if (Number.isNaN(target) || Number.isNaN(min))
            return get(_)("category.validationInvalidNumbers");
        if ((target ?? 0) < 0 || (min ?? 0) < 0) return get(_)("category.validationNonNegative");
        if (target !== null && min !== null && target < min)
            return get(_)("category.validationTargetGteMin");
        if (!form.name.trim()) return get(_)("category.validationNameRequired");
        if (form.parent_id === cat.id) return get(_)("category.validationSelfParent");
        return null;
    }

    async function saveCategory(cat: Category) {
        const form = forms.get(cat.id);
        if (!form) return;

        const msg = validateForm(cat, form);
        if (msg) {
            error = msg;
            return;
        }

        error = "";
        savingId = cat.id;
        try {
            const payload = {
                name: form.name.trim(),
                icon: form.icon.trim() || null,
                parent_id: form.parent_id,
                restock_target: parseNullableFloat(form.restock_target_input),
                restock_min: parseNullableFloat(form.restock_min_input),
                restock_inherit: form.restock_inherit,
            };
            const updated = await api.categories.update(cat.id, payload);
            categories = categories.map((c) => (c.id === updated.id ? updated : c));
            forms.set(updated.id, {
                name: updated.name,
                icon: updated.icon ?? "",
                parent_id: updated.parent_id,
                restock_target_input:
                    updated.restock_target === null ? "" : String(updated.restock_target),
                restock_min_input: updated.restock_min === null ? "" : String(updated.restock_min),
                restock_inherit: updated.restock_inherit,
            });
        } catch (e) {
            error = get(_)("category.failedToSave", { values: { error: String(e) } });
        } finally {
            savingId = null;
        }
    }

    function roots() {
        return (childrenByParentMap().get(null) ?? []).sort((a, b) => a.name.localeCompare(b.name));
    }

    function childrenOf(parentId: number) {
        return childrenByParentMap().get(parentId) ?? [];
    }

    function hasChildren(id: number): boolean {
        return childrenOf(id).length > 0;
    }
</script>

<div class="flex items-center justify-between gap-3 mt-0 mb-1">
    <h1 class="m-0">{$_("category.managementTitle")} ({categories.length})</h1>
    <button
        type="button"
        class="search-indicator"
        aria-label={$_("category.searchHint")}
        title={$_("category.searchHint")}
        onclick={() => (searchOpen = true)}
    >
        ⌕ {$_("common.searchIndicator")}
    </button>
</div>
<p class="text-gray-500 mt-1 mb-5">
    {$_("category.managementSubtitle")}
</p>

{#if loading}
    <p>{$_("common.loading")}</p>
{:else if error}
    <p class="text-[#e74c3c]">{error}</p>
{:else if categories.length === 0}
    <p class="text-center text-gray-500 my-10">
        {$_("category.emptyManagement")}
    </p>
{:else}
    <FuzzySearchOverlay
        items={categories}
        keys={["name", "icon"]}
        getId={(item) => (item as Category).id}
        getLabel={(item) => (item as Category).name}
        getSecondaryLabel={(item) => {
            const c = item as Category;
            if (c.parent_id == null) return $_("category.noParent");
            const parent = categories.find((p) => p.id === c.parent_id);
            return parent ? parent.name : $_("common.unknown");
        }}
        onSelect={selectCategoryFromSearch}
        placeholder={$_("category.searchPlaceholder")}
        noResultsText={$_("category.searchNoResults")}
        hintText={$_("category.searchHint")}
        bind:open={searchOpen}
    />

    <div class="tree">
        {#each roots() as root (root.id)}
            {@const rootForm = forms.get(root.id)!}
            {@const rootEff = computeEffectivePreview(root.id)}
            <section class="node-card" data-category-id={root.id}>
                <header class="node-head">
                    <button
                        class="collapse-btn"
                        onclick={() => toggleExpand(root.id)}
                        title={expanded.has(root.id)
                            ? $_("category.collapse")
                            : $_("category.expand")}
                    >
                        {expanded.has(root.id) ? "▾" : "▸"}
                    </button>
                    <strong>{root.name}</strong>
                    <span class="pill">{$_("category.idLabel", { values: { id: root.id } })}</span>
                </header>

                {#if expanded.has(root.id)}
                    <div class="grid">
                        <label>
                            {$_("category.nameLabel")}
                            <input bind:value={rootForm.name} />
                        </label>
                        <label>
                            {$_("category.editIcon")}
                            <input
                                bind:value={rootForm.icon}
                                placeholder={$_("category.iconPlaceholder")}
                            />
                        </label>
                        <label>
                            {$_("category.parentLabel")}
                            <select
                                bind:value={rootForm.parent_id}
                                onchange={(e) => {
                                    const val = (e.currentTarget as HTMLSelectElement).value;
                                    rootForm.parent_id = val === ROOT_PARENT ? null : Number(val);
                                }}
                            >
                                <option value={ROOT_PARENT}>{$_("category.noParent")}</option>
                                {#each parentOptionsFor(root) as option (option.id)}
                                    <option value={option.id}>{option.name}</option>
                                {/each}
                            </select>
                        </label>
                        <label class="toggle">
                            <input type="checkbox" bind:checked={rootForm.restock_inherit} />
                            {$_("category.inheritLabel")}
                        </label>
                        <label>
                            {$_("category.restockTargetLabel")}
                            <input
                                type="number"
                                min="0"
                                step="0.01"
                                bind:value={rootForm.restock_target_input}
                            />
                        </label>
                        <label>
                            {$_("category.restockMinLabel")}
                            <input
                                type="number"
                                min="0"
                                step="0.01"
                                bind:value={rootForm.restock_min_input}
                            />
                        </label>
                    </div>

                    <div class="effective">
                        <div>
                            <strong>{$_("category.effectiveTarget")}:</strong>
                            {rootEff.target ?? $_("category.unset")}
                        </div>
                        <div>
                            <strong>{$_("category.effectiveMin")}:</strong>
                            {rootEff.min ?? $_("category.unset")}
                        </div>
                        <div class="muted">
                            {$_("category.sourceTarget", {
                                values: { name: sourceLabel(rootEff.targetFrom) },
                            })} ·
                            {$_("category.sourceMin", {
                                values: { name: sourceLabel(rootEff.minFrom) },
                            })}
                        </div>
                    </div>

                    <div class="actions">
                        <button
                            class="save"
                            disabled={savingId === root.id}
                            onclick={() => saveCategory(root)}
                        >
                            {savingId === root.id
                                ? $_("category.saving")
                                : $_("category.saveButton")}
                        </button>
                    </div>
                {/if}

                {#if hasChildren(root.id) && expanded.has(root.id)}
                    <div class="children">
                        {#each childrenOf(root.id) as child (child.id)}
                            {@const childForm = forms.get(child.id)!}
                            {@const childEff = computeEffectivePreview(child.id)}
                            <article class="child-card" data-category-id={child.id}>
                                <header class="child-head">
                                    <button
                                        class="collapse-btn"
                                        onclick={() => toggleExpand(child.id)}
                                        title={expanded.has(child.id)
                                            ? $_("category.collapse")
                                            : $_("category.expand")}
                                    >
                                        {expanded.has(child.id) ? "▾" : "▸"}
                                    </button>
                                    <strong>{child.name}</strong>
                                    <span class="pill"
                                        >{$_("category.idLabel", {
                                            values: { id: child.id },
                                        })}</span
                                    >
                                </header>

                                {#if expanded.has(child.id)}
                                    <div class="grid">
                                        <label>
                                            {$_("category.nameLabel")}
                                            <input bind:value={childForm.name} />
                                        </label>
                                        <label>
                                            {$_("category.editIcon")}
                                            <input
                                                bind:value={childForm.icon}
                                                placeholder={$_("category.iconPlaceholder")}
                                            />
                                        </label>
                                        <label>
                                            {$_("category.parentLabel")}
                                            <select
                                                bind:value={childForm.parent_id}
                                                onchange={(e) => {
                                                    const val = (
                                                        e.currentTarget as HTMLSelectElement
                                                    ).value;
                                                    childForm.parent_id =
                                                        val === ROOT_PARENT ? null : Number(val);
                                                }}
                                            >
                                                <option value={ROOT_PARENT}
                                                    >{$_("category.noParent")}</option
                                                >
                                                {#each parentOptionsFor(child) as option (option.id)}
                                                    <option value={option.id}>{option.name}</option>
                                                {/each}
                                            </select>
                                        </label>
                                        <label class="toggle">
                                            <input
                                                type="checkbox"
                                                bind:checked={childForm.restock_inherit}
                                            />
                                            {$_("category.inheritLabel")}
                                        </label>
                                        <label>
                                            {$_("category.restockTargetLabel")}
                                            <input
                                                type="number"
                                                min="0"
                                                step="0.01"
                                                bind:value={childForm.restock_target_input}
                                            />
                                        </label>
                                        <label>
                                            {$_("category.restockMinLabel")}
                                            <input
                                                type="number"
                                                min="0"
                                                step="0.01"
                                                bind:value={childForm.restock_min_input}
                                            />
                                        </label>
                                    </div>

                                    <div class="effective">
                                        <div>
                                            <strong>{$_("category.effectiveTarget")}:</strong>
                                            {childEff.target ?? $_("category.unset")}
                                        </div>
                                        <div>
                                            <strong>{$_("category.effectiveMin")}:</strong>
                                            {childEff.min ?? $_("category.unset")}
                                        </div>
                                        <div class="muted">
                                            {$_("category.sourceTarget", {
                                                values: { name: sourceLabel(childEff.targetFrom) },
                                            })} ·
                                            {$_("category.sourceMin", {
                                                values: { name: sourceLabel(childEff.minFrom) },
                                            })}
                                        </div>
                                    </div>

                                    <div class="actions">
                                        <button
                                            class="save"
                                            disabled={savingId === child.id}
                                            onclick={() => saveCategory(child)}
                                        >
                                            {savingId === child.id
                                                ? $_("category.saving")
                                                : $_("category.saveButton")}
                                        </button>
                                    </div>
                                {/if}
                            </article>
                        {/each}
                    </div>
                {/if}
            </section>
        {/each}
    </div>
{/if}

<style>
    .tree {
        display: grid;
        gap: 1rem;
    }

    .node-card,
    .child-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1rem;
    }

    .children {
        margin-top: 0.8rem;
        display: grid;
        gap: 0.8rem;
        padding-left: 1rem;
        border-left: 2px dashed #e5e7eb;
    }

    .node-head,
    .child-head {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.8rem;
    }

    .collapse-btn {
        width: 1.7rem;
        height: 1.7rem;
        border-radius: 0.4rem;
        border: 1px solid #d1d5db;
        background: #f9fafb;
        cursor: pointer;
    }

    .pill {
        margin-left: auto;
        font-size: 0.75rem;
        color: #6b7280;
        background: #f3f4f6;
        border-radius: 999px;
        padding: 0.15rem 0.5rem;
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
        color: #4b5563;
    }

    input,
    select {
        border: 1px solid #d1d5db;
        border-radius: 8px;
        padding: 0.5rem 0.6rem;
        font-size: 0.95rem;
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
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        font-size: 0.9rem;
    }

    .muted {
        color: #6b7280;
        font-size: 0.8rem;
        margin-top: 0.2rem;
    }

    .actions {
        margin-top: 0.7rem;
        display: flex;
        justify-content: flex-end;
    }

    .save {
        background: #1a1a2e;
        color: white;
        border: 0;
        border-radius: 8px;
        padding: 0.45rem 0.9rem;
        font-weight: 600;
        cursor: pointer;
    }

    .save:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .search-indicator {
        font-size: 0.78rem;
        color: #6b7280;
        background: #f3f4f6;
        border: 1px solid #e5e7eb;
        border-radius: 999px;
        padding: 0.2rem 0.55rem;
        white-space: nowrap;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
    }

    .search-indicator:hover {
        background: #eef2ff;
        color: #374151;
        border-color: #c7d2fe;
    }

    .search-indicator:focus-visible {
        outline: 2px solid #6366f1;
        outline-offset: 2px;
    }
</style>
