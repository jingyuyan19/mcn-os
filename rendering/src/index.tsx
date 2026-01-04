import { registerRoot } from 'remotion';
import { Composition } from 'remotion';
import { MainComposition } from './Composition';
import { TimelineSchema } from './types';
import './index.css';
import "@fontsource/noto-sans-sc/700.css"; // Bold font


import { z } from 'zod';

export const RemotionRoot: React.FC = () => {
    return (
        <>
            <Composition
                id="MainVideo"
                component={MainComposition}
                fps={30}
                width={1080}
                height={1920}
                // Fix: dynamic duration from props
                calculateMetadata={async ({ props }) => {
                    return {
                        durationInFrames: props.timeline.durationInFrames || 90,
                    };
                }}
                // Fix: Schema must match the inputProps structure { timeline: ... }
                schema={z.object({
                    timeline: TimelineSchema
                })}
                defaultProps={{
                    timeline: {
                        width: 1080, height: 1920, fps: 30, durationInFrames: 90,
                        audioSrc: '', clips: [], subtitles: []
                    }
                }}
            />
        </>
    );
};

registerRoot(RemotionRoot);
