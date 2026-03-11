<script lang="ts">
    import { _ } from "svelte-i18n";

    import LocaleSwitcher from "$lib/components/LocaleSwitcher.svelte";
    import { page } from "$app/state";
    import "../app.css";

    let { children } = $props();
</script>

<svelte:head>
    <link rel="icon" type="image/png" href="/favicon-96x96.png" sizes="96x96" />
    <link rel="icon" href="/favicon.ico" />
    <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
    <meta name="apple-mobile-web-app-title" content="ChamberOfSecrets" />
    <link rel="manifest" href="/site.webmanifest" />
    <title>Chamber of Secrets</title>
</svelte:head>

<div class="layout-root" class:chamber-bg={page.url.pathname === "/chamber"}>
    <nav class="site-nav bg-[#1a1a2e] text-white px-6 flex items-center gap-8 h-12">
        <a href="/" class="font-bold text-[1.1rem] text-white no-underline">Chamber of Secrets</a>
        <ul class="list-none flex gap-4 m-0 p-0 flex-1">
            <li>
                <a
                    href="/chamber"
                    aria-current={page.url.pathname === "/chamber" ? "page" : undefined}
                    class="nav-link">{$_("nav.chamber")}</a
                >
            </li>
            <li>
                <a
                    href="/scan"
                    aria-current={page.url.pathname === "/scan" ? "page" : undefined}
                    class="nav-link">{$_("nav.scan")}</a
                >
            </li>
            <li>
                <a
                    href="/inventory"
                    aria-current={page.url.pathname === "/inventory" ? "page" : undefined}
                    class="nav-link">{$_("nav.inventory")}</a
                >
            </li>
            <li>
                <a
                    href="/analytics"
                    aria-current={page.url.pathname === "/analytics" ? "page" : undefined}
                    class="nav-link">{$_("nav.analytics")}</a
                >
            </li>
            <li>
                <a
                    href="/docs"
                    aria-current={page.url.pathname === "/docs" ? "page" : undefined}
                    class="nav-link">{$_("nav.docs")}</a
                >
            </li>
        </ul>
        <LocaleSwitcher />
    </nav>

    <main class="content-root">
        <div
            class:content-shell={page.url.pathname !== "/chamber"}
            class:chamber-shell={page.url.pathname === "/chamber"}
        >
            {@render children()}
        </div>
    </main>
</div>

<style>
    .layout-root {
        min-height: 100vh;
        background: white;
        display: flex;
        flex-direction: column;
    }

    .site-nav {
        position: relative;
        z-index: 10;
        flex: 0 0 auto;
    }

    .content-root {
        flex: 1 1 auto;
        min-height: 0;
    }

    .chamber-bg .content-root {
        background:
            url("/chamber-background.png") center / contain no-repeat,
            radial-gradient(
                ellipse at center,
                rgb(57, 47, 25) 0%,
                rgb(48, 39, 21) 72%,
                rgb(28, 22, 12) 100%
            );
    }

    .content-shell {
        max-width: 960px;
        margin: 0 auto;
        padding: 1.5rem;
    }

    .chamber-shell {
        max-width: none;
        width: 100%;
        height: 100%;
        margin: 0;
        padding: 0;
    }

    .nav-link {
        color: #d1d5db;
        text-decoration: none;
        padding: 0.4rem 0.8rem;
        border-radius: 6px;
        transition: background 0.2s;
    }

    .nav-link:hover,
    .nav-link[aria-current="page"] {
        background: rgba(255, 255, 255, 0.1);
        color: white;
    }

    .nav-link[aria-current="page"] {
        background: rgba(255, 255, 255, 0.15);
    }
</style>
