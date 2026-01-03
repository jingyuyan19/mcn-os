import React from 'react';
import { AbsoluteFill, Audio, Sequence, Video, Img, useVideoConfig } from 'remotion';
import timelineData from './timeline.json';

// Define types based on our JSON schema
type Style = {
    fontSize?: number;
    color?: string;
    top?: number;
    fontFamily?: string;
};

type OverlayItem = {
    id: string;
    type: 'text' | 'image';
    content: string; // text content or image url
    startFrame: number;
    durationInFrames: number;
    style?: Style;
};

type VideoItem = {
    id: string;
    type: 'video';
    src: string;
    startFrame: number;
    durationInFrames: number;
    offset?: number;
};

type AudioItem = {
    id: string;
    type: 'audio';
    src: string;
    startFrame: number;
    durationInFrames: number;
};

export const McnComposition: React.FC = () => {
    const { fps } = useVideoConfig(); // Access config if needed
    const { tracks, width, height } = timelineData;

    return (
        <AbsoluteFill style={{ backgroundColor: 'black' }}>
            {/* Video Track */}
            {tracks.video.map((clip: VideoItem) => (
                <Sequence
                    key={clip.id}
                    from={clip.startFrame}
                    durationInFrames={clip.durationInFrames}
                >
                    <Video
                        src={clip.src}
                        startFrom={clip.offset || 0}
                        style={{
                            width: '100%',
                            height: '100%',
                            objectFit: 'cover',
                        }}
                    />
                </Sequence>
            ))}

            {/* Audio Track */}
            {tracks.audio.map((clip: AudioItem) => (
                <Sequence
                    key={clip.id}
                    from={clip.startFrame}
                    durationInFrames={clip.durationInFrames}
                >
                    <Audio src={clip.src} />
                </Sequence>
            ))}

            {/* Overlay Track */}
            {tracks.overlay.map((item: OverlayItem) => (
                <Sequence
                    key={item.id}
                    from={item.startFrame}
                    durationInFrames={item.durationInFrames}
                >
                    {item.type === 'text' ? (
                        <div
                            style={{
                                position: 'absolute',
                                top: item.style?.top ?? 100,
                                width: '100%',
                                textAlign: 'center',
                                fontSize: item.style?.fontSize ?? 60,
                                color: item.style?.color ?? 'white',
                                fontFamily: item.style?.fontFamily ?? 'sans-serif',
                                fontWeight: 'bold',
                                textShadow: '0px 0px 10px rgba(0,0,0,0.8)',
                            }}
                        >
                            {item.content}
                        </div>
                    ) : (
                        <Img
                            src={item.content}
                            style={{
                                position: 'absolute',
                                top: item.style?.top ?? 0,
                                width: '100%', // simplistic styling
                            }}
                        />
                    )}
                </Sequence>
            ))}
        </AbsoluteFill>
    );
};
