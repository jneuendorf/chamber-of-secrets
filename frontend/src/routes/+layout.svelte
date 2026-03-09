<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import LocaleSwitcher from '$lib/components/LocaleSwitcher.svelte';
	import { _ } from 'svelte-i18n';
	import { page } from '$app/state';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Chamber of Secrets</title>
</svelte:head>

<div class="min-h-screen">
	<nav class="bg-[#1a1a2e] text-white px-6 flex items-center gap-8 h-12">
		<a href="/" class="font-bold text-[1.1rem] text-white no-underline">Chamber of Secrets</a>
		<ul class="list-none flex gap-4 m-0 p-0 flex-1">
			<li>
				<a
					href="/scan"
					aria-current={page.url.pathname === '/scan' ? 'page' : undefined}
					class="nav-link"
				>{$_('nav.scan')}</a>
			</li>
			<li>
				<a
					href="/inventory"
					aria-current={page.url.pathname === '/inventory' ? 'page' : undefined}
					class="nav-link"
				>{$_('nav.inventory')}</a>
			</li>
			<li>
				<a
					href="/analytics"
					aria-current={page.url.pathname === '/analytics' ? 'page' : undefined}
					class="nav-link"
				>{$_('nav.analytics')}</a>
			</li>
			<li>
				<a
					href="/docs"
					aria-current={page.url.pathname === '/docs' ? 'page' : undefined}
					class="nav-link"
				>{$_('nav.docs')}</a>
			</li>
		</ul>
		<LocaleSwitcher />
	</nav>

	<main class="max-w-[960px] mx-auto p-6">
		{@render children()}
	</main>
</div>

<style>
	.nav-link {
		color: #d1d5db;
		text-decoration: none;
		padding: 0.4rem 0.8rem;
		border-radius: 6px;
		transition: background 0.2s;
	}

	.nav-link:hover,
	.nav-link[aria-current='page'] {
		background: rgba(255, 255, 255, 0.1);
		color: white;
	}

	.nav-link[aria-current='page'] {
		background: rgba(255, 255, 255, 0.15);
	}
</style>
