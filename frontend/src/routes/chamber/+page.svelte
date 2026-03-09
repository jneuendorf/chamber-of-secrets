<script lang="ts">
	import { _ } from 'svelte-i18n';
	import { api, type Product } from '$lib/api/client';

	let products: Product[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let statsOpen = $state(false);

	$effect(() => {
		api.products
			.list()
			.then((p) => {
				products = p;
			})
			.catch((e) => {
				error = String(e);
			})
			.finally(() => {
				loading = false;
			});
	});

	// --- Emoji lookup ---
	function emojiFor(name: string, category: string | null): string {
		const t = [name, category ?? ''].join(' ').toLowerCase();
		if (/milk|milch|lait|vollmilch|skimmed|dairy|molkerei/.test(t)) return '🥛';
		if (/egg|ei\b|eier|oeuf/.test(t)) return '🥚';
		if (/bread|brot|pain|toast|baguette|brötchen/.test(t)) return '🍞';
		if (/cheese|käse|fromage/.test(t)) return '🧀';
		if (/butter/.test(t)) return '🧈';
		if (/yogu?rt|joghurt/.test(t)) return '🫙';
		if (/cream|sahne|crème/.test(t)) return '🍦';
		if (/apple|apfel|pomme/.test(t)) return '🍎';
		if (/banana|banane/.test(t)) return '🍌';
		if (/orange/.test(t)) return '🍊';
		if (/lemon|zitrone|citron/.test(t)) return '🍋';
		if (/strawberr|erdbeere/.test(t)) return '🍓';
		if (/cherry|kirsche|cerise/.test(t)) return '🍒';
		if (/grape|traube|weintraube|raisin/.test(t)) return '🍇';
		if (/pineapple|ananas/.test(t)) return '🍍';
		if (/mango/.test(t)) return '🥭';
		if (/avocado/.test(t)) return '🥑';
		if (/peach|pfirsich|pêche/.test(t)) return '🍑';
		if (/pear|birne|poire/.test(t)) return '🍐';
		if (/melon|melone/.test(t)) return '🍈';
		if (/kiwi/.test(t)) return '🥝';
		if (/tomato|tomate/.test(t)) return '🍅';
		if (/carrot|karotte|möhre|rübe/.test(t)) return '🥕';
		if (/potato|kartoffel|pommes/.test(t)) return '🥔';
		if (/broccoli|brokkoli/.test(t)) return '🥦';
		if (/corn|mais/.test(t)) return '🌽';
		if (/cucumber|gurke|concombre/.test(t)) return '🥒';
		if (/pepper|paprika/.test(t)) return '🫑';
		if (/onion|zwiebel|oignon/.test(t)) return '🧅';
		if (/garlic|knoblauch|ail/.test(t)) return '🧄';
		if (/lettuce|kopfsalat|laitue/.test(t)) return '🥬';
		if (/mushroom|pilz|champignon/.test(t)) return '🍄';
		if (/eggplant|aubergine/.test(t)) return '🍆';
		if (/chicken|hähnchen|poulet|hühn/.test(t)) return '🍗';
		if (/ham|schinken|jambon/.test(t)) return '🍖';
		if (/sausage|wurst|bratwurst|salami|würst/.test(t)) return '🌭';
		if (/beef|steak|rind|fleisch|meat|viande/.test(t)) return '🥩';
		if (/fish|fisch|lachs|salmon|thun|tuna|forelle|trout/.test(t)) return '🐟';
		if (/shrimp|garnele|prawn|crevette/.test(t)) return '🦐';
		if (/coffee|kaffee|espresso|cappuccino|latte/.test(t)) return '☕';
		if (/tea|tee|thé/.test(t)) return '🍵';
		if (/juice|saft|jus/.test(t)) return '🧃';
		if (/water|wasser|eau/.test(t)) return '💧';
		if (/beer|bier|bière/.test(t)) return '🍺';
		if (/wine|wein|vin/.test(t)) return '🍷';
		if (/cola|soda|limo|limonade|softdrink/.test(t)) return '🥤';
		if (/chocolate|schokolade|kakao|chocolat/.test(t)) return '🍫';
		if (/pasta|nudel|spaghetti|penne|fusilli|tagliatelle/.test(t)) return '🍝';
		if (/rice|reis|riz/.test(t)) return '🍚';
		if (/pizza/.test(t)) return '🍕';
		if (/burger/.test(t)) return '🍔';
		if (/cereal|müsli|muesli|granola|haferflocken|oat/.test(t)) return '🥣';
		if (/oil|öl|olive|huile/.test(t)) return '🫒';
		if (/salt|salz|sel/.test(t)) return '🧂';
		if (/sugar|zucker|sucre/.test(t)) return '🍬';
		if (/honey|honig|miel/.test(t)) return '🍯';
		if (/jam|marmelade|confiture/.test(t)) return '🫙';
		if (/sauce|ketchup|mustard|senf/.test(t)) return '🥫';
		if (/soup|suppe|bouillon/.test(t)) return '🍲';
		if (/nut|nuss|peanut|cashew|almond|mandel|haselnuss/.test(t)) return '🥜';
		if (/cookie|keks|biscuit/.test(t)) return '🍪';
		if (/cake|torte|kuchen/.test(t)) return '🎂';
		if (/chip|crisp|snack|cracker/.test(t)) return '🥨';
		if (/bean|bohne/.test(t)) return '🫘';
		if (/pea|erbse/.test(t)) return '🫛';
		if (/tofu/.test(t)) return '🧆';
		if (/frozen|tiefkühl|surgelé/.test(t)) return '🧊';
		return '📦';
	}

	// --- Deterministic positioning ---

	// djb2-style hash → unsigned 32-bit
	function hash(s: string): number {
		let h = 5381;
		for (let i = 0; i < s.length; i++) {
			h = (((h << 5) + h) ^ s.charCodeAt(i)) >>> 0;
		}
		return h;
	}

	// Cluster zones: natural spots in the dungeon scene.
	// (x%, y%) as % of the canvas. Avoids the centre-top where the snake sits.
	const ZONES = [
		{ cx: 10, cy: 62 }, // left chest pile
		{ cx: 18, cy: 74 }, // left floor
		{ cx: 6,  cy: 81 }, // far-left corner
		{ cx: 32, cy: 70 }, // centre-left floor
		{ cx: 50, cy: 76 }, // centre floor (bags)
		{ cx: 66, cy: 70 }, // centre-right floor
		{ cx: 78, cy: 62 }, // right barrel area
		{ cx: 84, cy: 74 }, // right floor
		{ cx: 91, cy: 81 }, // far-right corner
	];

	function productPos(catName: string, productId: number): { x: number; y: number } {
		const h1 = hash(catName);
		const zone = ZONES[h1 % ZONES.length];
		const h2 = hash(catName + String(productId));
		// Spread: ±10% x, ±6% y — outliers are natural
		const dx = ((h2 & 0xff) / 255 - 0.5) * 20;
		const dy = (((h2 >> 8) & 0xff) / 255 - 0.5) * 12;
		return {
			x: Math.max(3, Math.min(91, zone.cx + dx)),
			y: Math.max(47, Math.min(87, zone.cy + dy))
		};
	}

	// --- Derived values ---
	let maxStock = $derived(Math.max(1, ...products.map((p) => p.stock)));

	function emojiCount(stock: number): number {
		if (stock <= 0) return 0;
		return Math.max(1, Math.round((stock / maxStock) * 10));
	}

	let grouped = $derived(
		(() => {
			const map = new Map<string, Product[]>();
			for (const p of products) {
				const key = p.category?.name ?? '?';
				if (!map.has(key)) map.set(key, []);
				map.get(key)!.push(p);
			}
			return [...map.entries()].sort((a, b) => {
				const sumA = a[1].reduce((s, p) => s + p.stock, 0);
				const sumB = b[1].reduce((s, p) => s + p.stock, 0);
				return sumB - sumA;
			});
		})()
	);

	let available = $derived(products.filter((p) => p.stock > 0).length);
	let depleted = $derived(products.filter((p) => p.stock <= 0).length);
	let totalItems = $derived(products.reduce((s, p) => s + Math.max(0, p.stock), 0));

	function isUrl(s: string) {
		return s.startsWith('http') || s.startsWith('data:');
	}
</script>

<div class="chamber-root">
	<!-- Title floats over the scene -->
	<header class="chamber-header">
		<h1 class="chamber-title">⚗️ {$_('chamber.title')} 🗝️</h1>
	</header>

	{#if loading}
		<p class="state-msg">{$_('common.loading')}</p>
	{:else if error}
		<p class="state-msg error-msg">{error}</p>
	{:else if products.length === 0}
		<div class="empty-state">
			<p class="empty-icon">🏚️</p>
			<p class="empty-text">{$_('chamber.empty')}</p>
			<a href="/scan" class="cta-link">{$_('chamber.scanCta')}</a>
		</div>
	{:else}
		<!-- Full-scene canvas: products scattered as absolute clusters -->
		<div class="scene">
			{#each grouped as [catName, items]}
				{#each items as product (product.id)}
					{@const pos = productPos(catName, product.id)}
					{@const catIcon = product.category?.icon ?? null}
					{@const emoji =
						catIcon && !isUrl(catIcon)
							? catIcon
							: emojiFor(product.name, product.category?.name ?? null)}
					{@const count = emojiCount(product.stock)}
					<div
						class="cluster"
						class:depleted={product.stock <= 0}
						style="left:{pos.x}%;top:{pos.y}%"
					>
						<div class="pile">
							{#if count === 0}
								{#if catIcon && isUrl(catIcon)}
									<img src={catIcon} alt="" class="e img-e depleted-e" />
								{:else}
									<span class="e depleted-e">{emoji}</span>
								{/if}
							{:else}
								{#each Array.from({ length: count }) as _}
									{#if catIcon && isUrl(catIcon)}
										<img src={catIcon} alt="" class="e img-e" />
									{:else}
										<span class="e">{emoji}</span>
									{/if}
								{/each}
							{/if}
						</div>
						<span class="label">{product.name}{product.stock > 1 ? ` ×${product.stock}` : ''}</span>
					</div>
				{/each}
			{/each}
		</div>
	{/if}
</div>

<!-- Floating stats toggle -->
{#if !loading && products.length > 0}
	<button class="stats-btn" onclick={() => (statsOpen = true)} title={$_('chamber.statsTitle')}>
		📜
	</button>
{/if}

<!-- Stats modal -->
{#if statsOpen}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div class="modal-backdrop" onclick={() => (statsOpen = false)}>
		<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
		<div class="modal-card" onclick={(e) => e.stopPropagation()}>
			<h2 class="modal-title">📜 {$_('chamber.statsTitle')}</h2>
			<table class="stats-table">
				<tbody>
					<tr>
						<td>{$_('chamber.available')}</td>
						<td class="stat-val">{available}</td>
					</tr>
					<tr>
						<td>{$_('chamber.required')}</td>
						<td class="stat-val" class:stat-depleted={depleted > 0}>{depleted}</td>
					</tr>
					<tr>
						<td>{$_('chamber.totalStock')}</td>
						<td class="stat-val">{totalItems}</td>
					</tr>
				</tbody>
			</table>
			{#if grouped.length > 0}
				<div class="divider"></div>
				<table class="stats-table">
					<tbody>
						{#each grouped as [catName, items]}
							{@const catStock = items.reduce((s, p) => s + Math.max(0, p.stock), 0)}
							<tr>
								<td class="stat-cat">{catName}</td>
								<td class="stat-val">{catStock}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}
			<button class="close-btn" onclick={() => (statsOpen = false)}>
				{$_('chamber.close')}
			</button>
		</div>
	</div>
{/if}

<style>
	/* ---- Background: snake always visible at top ---- */
	.chamber-root::before {
		content: '';
		position: fixed;
		inset: 0;
		background: url('/chamber-background.png') top center / cover no-repeat;
		background-color: #0a0a14;
		z-index: -1;
	}

	/* ---- Root: full viewport canvas ---- */
	.chamber-root {
		margin: -1.5rem;
		height: calc(100vh - 3rem);
		overflow: hidden;
		position: relative;
		color: #e0e0ff;
	}

	/* ---- Floating title ---- */
	.chamber-header {
		position: absolute;
		top: 1rem;
		left: 50%;
		transform: translateX(-50%);
		z-index: 5;
		white-space: nowrap;
	}

	.chamber-title {
		display: inline-block;
		margin: 0;
		font-size: clamp(1.1rem, 3.5vw, 1.7rem);
		font-weight: 900;
		letter-spacing: 0.15em;
		text-transform: uppercase;
		color: #ffd700;
		text-shadow: 0 2px 10px rgba(0, 0, 0, 1);
		background: rgba(0, 0, 0, 0.55);
		padding: 0.4rem 1.2rem;
		border-radius: 8px;
		border: 1px solid rgba(255, 215, 0, 0.3);
	}

	/* ---- Scene canvas ---- */
	.scene {
		position: absolute;
		inset: 0;
	}

	/* ---- Product cluster ---- */
	.cluster {
		position: absolute;
		transform: translate(-50%, -100%);
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2px;
		cursor: default;
	}

	.cluster.depleted {
		opacity: 0.35;
		filter: grayscale(0.7);
	}

	/* ---- Emoji pile ---- */
	.pile {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		max-width: 5.5rem;
		gap: 0;
		line-height: 1;
		/* Slight drop-shadow so emojis pop from the background */
		filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.8));
	}

	.e {
		font-size: clamp(1.2rem, 2.2vw, 1.6rem);
	}

	.img-e {
		width: clamp(1.2rem, 2.2vw, 1.6rem);
		height: clamp(1.2rem, 2.2vw, 1.6rem);
		object-fit: cover;
		border-radius: 3px;
		display: inline-block;
	}

	.depleted-e {
		filter: grayscale(1) opacity(0.4);
	}

	/* ---- Product label ---- */
	.label {
		font-size: 0.6rem;
		color: rgba(255, 255, 255, 0.75);
		text-shadow: 0 1px 3px rgba(0, 0, 0, 1), 0 0 6px rgba(0, 0, 0, 0.9);
		text-align: center;
		max-width: 6rem;
		line-height: 1.2;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	/* ---- State messages ---- */
	.state-msg {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		color: #e0e0ff;
		background: rgba(0, 0, 0, 0.6);
		padding: 1rem 1.5rem;
		border-radius: 8px;
	}

	.error-msg { color: #f87171; }

	.empty-state {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		text-align: center;
		background: rgba(0, 0, 0, 0.6);
		padding: 2.5rem 2rem;
		border-radius: 12px;
		border: 1px solid rgba(255, 215, 0, 0.2);
	}

	.empty-icon { font-size: 3rem; margin: 0 0 0.5rem; }
	.empty-text { color: #9ca3af; margin: 0 0 1rem; }

	.cta-link {
		display: inline-block;
		padding: 0.4rem 1.1rem;
		background: rgba(255, 215, 0, 0.12);
		border: 1px solid rgba(255, 215, 0, 0.35);
		border-radius: 6px;
		color: #fbbf24;
		text-decoration: none;
		font-size: 0.85rem;
	}

	/* ---- Stats button ---- */
	.stats-btn {
		position: fixed;
		bottom: 1.5rem;
		right: 1.5rem;
		width: 3rem;
		height: 3rem;
		font-size: 1.4rem;
		background: rgba(6, 4, 14, 0.88);
		border: 1px solid rgba(255, 215, 0, 0.45);
		border-radius: 50%;
		cursor: pointer;
		z-index: 20;
		display: flex;
		align-items: center;
		justify-content: center;
		box-shadow: 0 2px 14px rgba(0, 0, 0, 0.6);
	}

	.stats-btn:hover {
		background: rgba(20, 12, 40, 0.95);
		border-color: rgba(255, 215, 0, 0.75);
	}

	/* ---- Stats modal ---- */
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.72);
		z-index: 50;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem;
	}

	.modal-card {
		background: #0a0814;
		border: 1px solid rgba(255, 215, 0, 0.4);
		border-radius: 12px;
		padding: 1.5rem;
		min-width: 240px;
		max-width: 340px;
		width: 100%;
		box-shadow: 0 0 40px rgba(0, 0, 0, 0.85);
	}

	.modal-title {
		margin: 0 0 1rem;
		font-size: 0.78rem;
		letter-spacing: 0.22em;
		text-transform: uppercase;
		color: #fbbf24;
		text-align: center;
		font-weight: 700;
	}

	.stats-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.85rem;
	}

	.stats-table td {
		padding: 0.28rem 0;
		color: #d1d5db;
	}

	.stat-val {
		text-align: right;
		font-weight: 700;
		color: #e0e0ff;
	}

	.stat-depleted { color: #f87171; }
	.stat-cat { color: #9ca3af; font-size: 0.78rem; }

	.divider {
		height: 1px;
		background: rgba(255, 215, 0, 0.18);
		margin: 0.75rem 0;
	}

	.close-btn {
		margin-top: 1.1rem;
		width: 100%;
		padding: 0.5rem;
		background: rgba(255, 215, 0, 0.1);
		border: 1px solid rgba(255, 215, 0, 0.3);
		border-radius: 6px;
		color: #fbbf24;
		font-size: 0.75rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		cursor: pointer;
	}

	.close-btn:hover { background: rgba(255, 215, 0, 0.2); }
</style>
