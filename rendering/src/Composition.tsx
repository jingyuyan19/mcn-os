import React from 'react';
import { AbsoluteFill, Audio, Sequence, Video, Img, useVideoConfig } from 'remotion';
import { Timeline } from './types';
import './index.css';

// Asset Server URL (Localhost via Nginx)
const ASSET_HOST = process.env.ASSET_HOST || 'http://localhost:8081/assets/';

export const MainComposition: React.FC<{ timeline: Timeline }> = ({ timeline }) => {
    const { width, height } = useVideoConfig();

    return (
        <AbsoluteFill style={{ backgroundColor: '#1a1a1a' }}>

            {/* 🎵 1. Global Audio Layer */}
            {timeline.audioSrc && (
                <Audio src={`${ASSET_HOST}${timeline.audioSrc}`} />
            )}
            {timeline.bgmSrc && (
                <Audio
                    src={`${ASSET_HOST}${timeline.bgmSrc}`}
                    volume={0.1}
                    loop
                />
            )}

            {/* 🎞️ 2. Visual Layer Stack */}
            {[...timeline.clips]
                .sort((a, b) => a.layer - b.layer)
                .map((clip, i) => (
                    <Sequence
                        key={i}
                        from={clip.startFrame}
                        durationInFrames={clip.durationFrames}
                        layout="none"
                    >
                        <div style={{
                            zIndex: clip.layer,
                            position: 'absolute',
                            width: '100%', height: '100%',
                            ...clip.style
                        }}>
                            {clip.type !== 'image' ? (
                                <Video
                                    src={`${ASSET_HOST}${clip.src}`}
                                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                    // 🔇 SAFETY: Overlays must be silent to not clash with Avatar TTS
                                    volume={clip.layer > 0 ? 0 : 1}
                                />
                            ) : (
                                <Img
                                    src={`${ASSET_HOST}${clip.src}`}
                                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                />
                            )}
                        </div>
                    </Sequence>
                ))}

            {/* 📝 3. Subtitles Layer (Z=999) */}
            <Sequence from={0} style={{ zIndex: 999, pointerEvents: 'none' }}>
                <div style={{
                    position: 'absolute',
                    bottom: 150,
                    width: '100%',
                    textAlign: 'center',
                    fontFamily: 'Noto Sans SC',
                    fontSize: 60,
                    color: 'white',
                    textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
                    fontWeight: 'bold'
                }}>
                    {timeline.subtitles.map((sub, i) => (
                        <Sequence
                            key={i}
                            from={sub.startFrame}
                            durationInFrames={sub.endFrame - sub.startFrame}
                        >
                            {sub.text}
                        </Sequence>
                    ))}
                </div>
            </Sequence>

        </AbsoluteFill>
    );
};
