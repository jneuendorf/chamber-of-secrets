<script lang="ts">
    const apiBase = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api";
    const docsUrl = apiBase.replace(/\/api$/, "/api/docs");
</script>

<svelte:head>
    <title>API Docs – Chamber of Secrets</title>
</svelte:head>

<div class="fixed inset-0 top-12">
    <iframe src={docsUrl} title="OpenAPI / Swagger UI" class="w-full h-full border-0"></iframe>
</div>
