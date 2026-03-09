<script lang="ts">
	import { get } from 'svelte/store';
	import { _ } from 'svelte-i18n';

	let { onScan }: { onScan: (code: string) => void } = $props();

	let videoEl: HTMLVideoElement | undefined = $state();
	let stream: MediaStream | null = $state(null);
	let scanning = $state(false);
	let error = $state('');
	let manualCode = $state('');

	async function startCamera() {
		error = '';
		try {
			stream = await navigator.mediaDevices.getUserMedia({
				video: { facingMode: 'environment' }
			});
			if (videoEl) {
				videoEl.srcObject = stream;
				await videoEl.play();
				scanning = true;
				detectBarcode();
			}
		} catch (e) {
			error = get(_)('scanner.cameraError', { values: { error: String(e) } });
		}
	}

	function stopCamera() {
		scanning = false;
		stream?.getTracks().forEach((t) => t.stop());
		stream = null;
	}

	async function detectBarcode() {
		if (!scanning || !videoEl) return;

		if ('BarcodeDetector' in window) {
			const detector = new BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e'] });
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
			error = get(_)('scanner.unsupported');
			stopCamera();
		}
	}

	function submitManual() {
		const code = manualCode.trim();
		if (code) {
			onScan(code);
			manualCode = '';
		}
	}
</script>

<div class="flex flex-col items-center gap-4">
	{#if scanning}
		<div class="relative w-full max-w-[400px] rounded-xl overflow-hidden">
			<!-- svelte-ignore element_invalid_self_closing_tag -->
			<video bind:this={videoEl} playsinline class="w-full block" />
			<div class="absolute inset-0 border-2 border-white/30 rounded-xl flex items-center justify-center">
				<div class="scan-line"></div>
			</div>
			<button onclick={stopCamera} class="absolute bottom-4 right-4 bg-black/60 text-white border-0 px-4 py-2 rounded-md cursor-pointer">{$_('scanner.stop')}</button>
		</div>
	{:else}
		<button onclick={startCamera} class="px-8 py-4 text-lg bg-[#1a1a2e] text-white border-0 rounded-lg cursor-pointer">{$_('scanner.startCamera')}</button>
	{/if}

	{#if error}
		<p class="text-[#e74c3c] text-sm">{error}</p>
	{/if}

	<div class="w-full max-w-[400px]">
		<span class="block text-center text-gray-400 text-[0.85rem] my-2">{$_('scanner.orManual')}</span>
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
				placeholder={$_('scanner.barcodePlaceholder')}
				inputmode="numeric"
				pattern="[0-9]*"
				class="flex-1 px-2.5 py-[0.6rem] border border-gray-300 rounded-md text-base"
			/>
			<button type="submit" class="px-4 py-[0.6rem] bg-[#1a1a2e] text-white border-0 rounded-md cursor-pointer">{$_('scanner.lookUp')}</button>
		</form>
	</div>
</div>

<style>
	.scan-line {
		width: 80%;
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
