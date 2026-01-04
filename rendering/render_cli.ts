import { renderMedia, selectComposition } from '@remotion/renderer';
import { bundle } from '@remotion/bundler';
import path from 'path';
import fs from 'fs';

const start = async () => {
    const [, , jsonPath, outputPath] = process.argv;
    if (!jsonPath || !outputPath) throw new Error('Usage: ts-node render_cli.ts <json> <out>');

    console.log('📦 Reading Timeline:', jsonPath);
    const timeline = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));

    console.log('📦 Bundling...');
    const bundled = await bundle(path.join(__dirname, 'src/index.tsx'));

    const composition = await selectComposition({
        serveUrl: bundled,
        id: 'MainVideo',
        inputProps: { timeline },
    });

    console.log('🚀 Rendering (CPU Mode - Concurrency 1)...');
    await renderMedia({
        composition,
        serveUrl: bundled,
        codec: 'h264',
        outputLocation: outputPath,
        inputProps: { timeline },
        // 🛡️ SAFETY: Force CPU rendering to protect 4090 VRAM
        chromiumOptions: {
            gl: 'angle',
        },
        concurrency: 1, // 🛡️ SAFETY: Prevent CPU starvation of other services
        verbose: true,
    });

    console.log(`✅ Render done: ${outputPath}`);
};

start().catch((err) => {
    console.error('❌ Render Failed:', err);
    process.exit(1);
});
