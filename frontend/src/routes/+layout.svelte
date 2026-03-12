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
    <nav class="site-nav bg-[#1a1a2e] text-white">
        <div class="nav-main">
            <a href="/" class="brand-link">{$_("nav.brand")}</a>
            <div class="nav-links-wrap">
                <ul class="nav-links">
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
                    {#if page.url.searchParams.has("api")}
                        <li>
                            <a
                                href="/docs?api"
                                aria-current={page.url.pathname === "/docs" ? "page" : undefined}
                                class="nav-link">{$_("nav.docs")}</a
                            >
                        </li>
                    {/if}
                </ul>
            </div>
            <LocaleSwitcher />
        </div>
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
        width: 100%;
        min-width: 100%;
        min-height: 100vh;
        min-height: 100dvh;
        background: white;
        display: flex;
        flex-direction: column;
    }

    .site-nav {
        position: relative;
        z-index: 10;
        flex: 0 0 auto;
        padding: 0.5rem 1rem;
    }

    .nav-main {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .brand-link {
        font-weight: 700;
        font-size: 1.1rem;
        color: white;
        text-decoration: none;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        flex: 0 1 auto;
        min-width: 0;
    }

    .nav-links-wrap {
        flex: 1 1 auto;
        min-width: 0;
        overflow-x: auto;
        overflow-y: hidden;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: thin;
    }

    .nav-links {
        list-style: none;
        display: flex;
        gap: 0.35rem;
        margin: 0;
        padding: 0;
        min-width: max-content;
    }

    @media (max-width: 760px) {
        .site-nav {
            padding: 0.5rem 1rem 0.25rem;
        }

        .nav-main {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            grid-template-areas:
                "brand locale"
                "links links";
            align-items: center;
            row-gap: 0.35rem;
            column-gap: 0.75rem;
            min-height: 2.5rem;
        }

        .brand-link {
            grid-area: brand;
        }

        .nav-main :global(.flex.gap-1) {
            grid-area: locale;
            justify-self: end;
        }

        .nav-links-wrap {
            grid-area: links;
            margin-top: 0;
        }

        .nav-links {
            padding: 0 0 0.25rem;
        }
    }

    @media (min-width: 761px) {
        .nav-main :global(.flex.gap-1) {
            margin-left: auto;
            flex: 0 0 auto;
        }
    }

    .content-root {
        flex: 1 1 auto;
        min-height: 0;
        width: 100%;
        overflow: hidden;
    }

    .chamber-bg .content-root {
        background: radial-gradient(
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
        min-width: 100%;
        height: 100%;
        margin: 0;
        padding: 0;
    }

    .nav-link {
        display: inline-block;
        color: #d1d5db;
        text-decoration: none;
        padding: 0.35rem 0.7rem;
        border-radius: 6px;
        transition: background 0.2s;
        white-space: nowrap;
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
