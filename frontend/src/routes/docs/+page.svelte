<script lang="ts">
	const apiBase = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000/api'
	const docsUrl = apiBase.replace(/\/api$/, '/api/docs')
</script>

<svelte:head>
	<title>API Docs – Chamber of Secrets</title>
</svelte:head>

<div class="docs-container">
	<iframe src={docsUrl} title="OpenAPI / Swagger UI"></iframe>
</div>

<style>
	.docs-container {
		/* Break out of the layout's max-width and padding */
		position: fixed;
		top: var(--nav-height, 48px);
		left: 0;
		right: 0;
		bottom: 0;
	}

	iframe {
		width: 100%;
		height: 100%;
		border: none;
	}
</style>
