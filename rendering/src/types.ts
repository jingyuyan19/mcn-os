import { z } from 'zod';

// 1. Clip Definition
export const ClipSchema = z.object({
    type: z.enum(['avatar', 'product_vfx', 'b_roll', 'image']),
    src: z.string(),       // Relative path "temp/xxx.mp4"
    startFrame: z.number(),
    durationFrames: z.number(),
    layer: z.number(),     // Z-Index: 0=Base, 10=Overlay
    style: z.object({      // Optional CCS overrides
        scale: z.number().optional(),
        opacity: z.number().optional(),
        top: z.number().optional(),
        left: z.number().optional(),
    }).optional(),
});

// 2. Subtitle Definition
export const SubtitleSchema = z.object({
    text: z.string(),
    startFrame: z.number(),
    endFrame: z.number(),
});

// 3. Master Timeline
export const TimelineSchema = z.object({
    width: z.number().default(1080),
    height: z.number().default(1920),
    fps: z.number().default(30),
    audioSrc: z.string(), // Main TTS Audio
    bgmSrc: z.string().optional(),
    durationInFrames: z.number(),
    clips: z.array(ClipSchema),
    subtitles: z.array(SubtitleSchema),
});

export type Timeline = z.infer<typeof TimelineSchema>;
