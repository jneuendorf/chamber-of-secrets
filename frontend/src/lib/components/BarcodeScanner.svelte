<script lang="ts">
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
			error = `Camera access denied: ${e}`;
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
			error = 'BarcodeDetector API not supported. Use manual entry or try Chrome/Edge.';
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

<div class="scanner">
	{#if scanning}
		<div class="video-container">
			<!-- svelte-ignore element_invalid_self_closing_tag -->
			<video bind:this={videoEl} playsinline />
			<div class="overlay">
				<div class="scan-line"></div>
			</div>
			<button onclick={stopCamera} class="stop-btn">Stop</button>
		</div>
	{:else}
		<button onclick={startCamera} class="scan-btn">Start Camera Scan</button>
	{/if}

	{#if error}
		<p class="error">{error}</p>
	{/if}

	<div class="manual">
		<span class="divider">or enter barcode manually</span>
		<form
			onsubmit={(e) => {
				e.preventDefault();
				submitManual();
			}}
		>
			<input
				type="text"
				bind:value={manualCode}
				placeholder="Enter EAN / barcode"
				inputmode="numeric"
				pattern="[0-9]*"
			/>
			<button type="submit">Look up</button>
		</form>
	</div>
</div>

<style>
	.scanner {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
	}

	.video-container {
		position: relative;
		width: 100%;
		max-width: 400px;
		border-radius: 12px;
		overflow: hidden;
	}

	video {
		width: 100%;
		display: block;
	}

	.overlay {
		position: absolute;
		inset: 0;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-radius: 12px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

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

	.stop-btn {
		position: absolute;
		bottom: 1rem;
		right: 1rem;
		background: rgba(0, 0, 0, 0.6);
		color: white;
		border: none;
		padding: 0.5rem 1rem;
		border-radius: 6px;
		cursor: pointer;
	}

	.scan-btn {
		padding: 1rem 2rem;
		font-size: 1.1rem;
		background: #1a1a2e;
		color: white;
		border: none;
		border-radius: 8px;
		cursor: pointer;
	}

	.error {
		color: #e74c3c;
		font-size: 0.9rem;
	}

	.manual {
		width: 100%;
		max-width: 400px;
	}

	.divider {
		display: block;
		text-align: center;
		color: #999;
		font-size: 0.85rem;
		margin: 0.5rem 0;
	}

	.manual form {
		display: flex;
		gap: 0.5rem;
	}

	.manual input {
		flex: 1;
		padding: 0.6rem;
		border: 1px solid #ddd;
		border-radius: 6px;
		font-size: 1rem;
	}

	.manual button {
		padding: 0.6rem 1rem;
		background: #1a1a2e;
		color: white;
		border: none;
		border-radius: 6px;
		cursor: pointer;
	}
</style>
