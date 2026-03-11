// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
    namespace App {
        // interface Error {}
        // interface Locals {}
        // interface PageData {}
        // interface PageState {}
        // interface Platform {}
    }

    // BarcodeDetector API (Chrome/Edge)
    class BarcodeDetector {
        constructor(options?: { formats: string[] });
        detect(image: ImageBitmapSource): Promise<{ rawValue: string; format: string }[]>;
    }
}

export {};
