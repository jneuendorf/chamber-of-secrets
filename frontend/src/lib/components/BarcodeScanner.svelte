<script lang="ts">
    import { get } from "svelte/store";
    import { _ } from "svelte-i18n";
    import { tick } from "svelte";

    let { onScan }: { onScan: (code: string) => void } = $props();

    let videoEl: HTMLVideoElement | undefined = $state();
    let stream: MediaStream | null = null;
    let scanning = $state(false);
    let modalOpen = $state(false);
    let error = $state("");
    let manualCode = $state("");

    let cameras: MediaDeviceInfo[] = $state([]);
    let selectedDeviceId = $state("");

    async function enumerateCameras() {
        // getUserMedia must have been called first to get device labels
        const devices = await navigator.mediaDevices.enumerateDevices();
        cameras = devices.filter((d) => d.kind === "videoinput");
        if (cameras.length > 0 && !selectedDeviceId) {
            // Prefer rear/environment camera on mobile
            const rear = cameras.find((c) => /back|rear|environment/i.test(c.label));
            selectedDeviceId = rear?.deviceId ?? cameras[cameras.length - 1].deviceId;
        }
    }

    async function openStream() {
        stream?.getTracks().forEach((t) => t.stop());
        stream = null;
        scanning = false;

        const videoConstraints: MediaTrackConstraints = selectedDeviceId
            ? { deviceId: { exact: selectedDeviceId } }
            : { facingMode: "environment" };

        stream = await navigator.mediaDevices.getUserMedia({ video: videoConstraints });

        if (videoEl) {
            videoEl.srcObject = stream;
            await videoEl.play();
            scanning = true;
            detectBarcode();
        }
    }

    async function startCamera() {
        error = "";
        modalOpen = true;
        await tick();

        try {
            // Initial getUserMedia call to get permission + labels
            const tempStream = await navigator.mediaDevices.getUserMedia({ video: true });
            tempStream.getTracks().forEach((t) => t.stop());

            await enumerateCameras();
            await openStream();
        } catch (e) {
            error = get(_)("scanner.cameraError", { values: { error: String(e) } });
        }
    }

    async function switchCamera(deviceId: string) {
        selectedDeviceId = deviceId;
        scanning = false;
        try {
            await openStream();
        } catch (e) {
            error = get(_)("scanner.cameraError", { values: { error: String(e) } });
        }
    }

    function stopCamera() {
        scanning = false;
        stream?.getTracks().forEach((t) => t.stop());
        stream = null;
        modalOpen = false;
    }

    async function detectBarcode() {
        if (!scanning || !videoEl) return;

        if ("BarcodeDetector" in window) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const detector = new (window as any).BarcodeDetector({
                formats: ["ean_13", "ean_8", "upc_a", "upc_e"],
            });
            const detect = async () => {
                if (!scanning || !videoEl) return;
                try {
                    const barcodes = await detector.detect(videoEl);
                    if (barcodes.length > 0) {
                        stopCamera();
                        onScan(barcodes[0].rawValue);
                        return;
                    }
                } catch {
                    // Detection failed, retry
                }
                requestAnimationFrame(detect);
            };
            detect();
        } else {
            error = get(_)("scanner.unsupported");
            stopCamera();
        }
    }

    function submitManual() {
        const code = manualCode.trim();
        if (code) {
            onScan(code);
            manualCode = "";
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === "Escape") stopCamera();
    }
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="flex flex-col items-center gap-4">
    <button
        onclick={startCamera}
        class="px-8 py-4 text-lg bg-[#1a1a2e] text-white border-0 rounded-lg cursor-pointer"
    >
        {$_("scanner.startCamera")}
    </button>

    {#if error && !modalOpen}
        <p class="text-[#e74c3c] text-sm">{error}</p>
    {/if}

    <div class="w-full max-w-[400px]">
        <span class="block text-center text-gray-400 text-[0.85rem] my-2"
            >{$_("scanner.orManual")}</span
        >
        <form
            class="flex gap-2"
            onsubmit={(e) => {
                e.preventDefault();
                submitManual();
            }}
        >
            <input
                type="text"
                bind:value={manualCode}
                placeholder={$_("scanner.barcodePlaceholder")}
                inputmode="numeric"
                pattern="[0-9]*"
                class="flex-1 px-2.5 py-[0.6rem] border border-gray-300 rounded-md text-base"
            />
            <button
                type="submit"
                class="px-4 py-[0.6rem] bg-[#1a1a2e] text-white border-0 rounded-md cursor-pointer"
            >
                {$_("scanner.lookUp")}
            </button>
        </form>
    </div>
</div>

{#if modalOpen}
    <!-- Backdrop -->
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div
        class="fixed inset-0 bg-black/70 z-40 flex items-center justify-center p-4"
        onclick={(e) => {
            if (e.target === e.currentTarget) stopCamera();
        }}
    >
        <!-- Modal -->
        <div
            class="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden z-50 flex flex-col"
        >
            <!-- Header -->
            <div class="flex items-center justify-between px-4 py-3 border-b border-gray-200">
                <span class="font-semibold text-[#1a1a2e]">{$_("scanner.scanBarcode")}</span>
                <button
                    onclick={stopCamera}
                    class="text-gray-500 hover:text-gray-800 text-2xl leading-none border-0 bg-transparent cursor-pointer"
                    aria-label={$_("scanner.stop")}
                >
                    &times;
                </button>
            </div>

            <!-- Video feed -->
            <div class="relative bg-black aspect-video">
                <!-- svelte-ignore element_invalid_self_closing_tag -->
                <video bind:this={videoEl} playsinline class="w-full h-full object-cover block" />
                <!-- Scan overlay -->
                <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div
                        class="w-4/5 h-1/3 border-2 border-white/60 rounded-lg flex items-center justify-center"
                    >
                        {#if scanning}
                            <div class="scan-line"></div>
                        {/if}
                    </div>
                </div>
            </div>

            <!-- Camera selector + error -->
            <div class="px-4 py-3 flex flex-col gap-2">
                {#if error}
                    <p class="text-[#e74c3c] text-sm text-center">{error}</p>
                {/if}

                {#if cameras.length > 1}
                    <div class="flex items-center gap-2">
                        <label for="camera-select" class="text-sm text-gray-600 shrink-0">
                            {$_("scanner.camera")}
                        </label>
                        <select
                            id="camera-select"
                            class="flex-1 px-2 py-1.5 border border-gray-300 rounded-md text-sm"
                            value={selectedDeviceId}
                            onchange={(e) => switchCamera((e.target as HTMLSelectElement).value)}
                        >
                            {#each cameras as cam, i}
                                <option value={cam.deviceId}>
                                    {cam.label || `${$_("scanner.camera")} ${i + 1}`}
                                </option>
                            {/each}
                        </select>
                    </div>
                {/if}

                <button
                    onclick={stopCamera}
                    class="w-full py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 border-0 rounded-lg text-sm cursor-pointer"
                >
                    {$_("scanner.stop")}
                </button>
            </div>
        </div>
    </div>
{/if}

<style>
    .scan-line {
        width: 100%;
        height: 2px;
        background: #e74c3c;
        box-shadow: 0 0 8px rgba(231, 76, 60, 0.6);
        animation: pulse 1.5s ease-in-out infinite;
    }

    @keyframes pulse {
        0%,
        100% {
            opacity: 1;
        }
        50% {
            opacity: 0.3;
        }
    }
</style>
