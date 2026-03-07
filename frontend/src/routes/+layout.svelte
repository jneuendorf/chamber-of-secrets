<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Chamber of Secrets</title>
</svelte:head>

<div class="app">
	<nav>
		<a href="/" class="logo">Chamber of Secrets</a>
		<ul>
			<li><a href="/scan">Scan</a></li>
			<li><a href="/inventory">Inventory</a></li>
			<li><a href="/analytics">Analytics</a></li>
			<li><a href="/docs">API Docs</a></li>
		</ul>
	</nav>

	<main>
		{@render children()}
	</main>
</div>

<style>
	:global(body) {
		margin: 0;
		font-family:
			system-ui,
			-apple-system,
			sans-serif;
		background: #f5f5f5;
		color: #1a1a1a;
	}

	.app {
		min-height: 100vh;
	}

	nav {
		background: #1a1a2e;
		color: white;
		padding: 0.75rem 1.5rem;
		display: flex;
		align-items: center;
		gap: 2rem;
		height: 48px;
		box-sizing: border-box;
	}

	.logo {
		font-weight: 700;
		font-size: 1.1rem;
		color: white;
		text-decoration: none;
	}

	nav ul {
		list-style: none;
		display: flex;
		gap: 1rem;
		margin: 0;
		padding: 0;
	}

	nav a {
		color: #ccc;
		text-decoration: none;
		padding: 0.4rem 0.8rem;
		border-radius: 6px;
		transition: background 0.2s;
	}

	nav a:hover {
		background: rgba(255, 255, 255, 0.1);
		color: white;
	}

	main {
		max-width: 960px;
		margin: 0 auto;
		padding: 1.5rem;
	}
</style>
