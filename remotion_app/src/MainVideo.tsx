import React from 'react';
import { AbsoluteFill, Sequence, useCurrentFrame, Audio, Img, Video, interpolate, useVideoConfig, staticFile, spring } from 'remotion';

export type WordTiming = {
    word: string;
    start: number;
    end: number;
};

export type SlideData = {
    bgPath: string;
    isVideo: boolean;
    durationInFrames: number;
    startFrame: number;
    text: string;
};

export type MainVideoProps = {
    slides: SlideData[];
    audioUrl: string;
    bgmUrl?: string;
    wordTimings?: WordTiming[];
    isShorts: boolean;
    hookText?: string;
    title?: string;
};

// ─── Ken Burns Image ─────────────────────────────────────────
const KenBurnsImage: React.FC<{ src: string; duration: number }> = ({ src, duration }) => {
    const frame = useCurrentFrame();
    const scale = interpolate(frame, [0, duration], [1, 1.15], {
        extrapolateRight: 'clamp',
    });

    if (!src) return <div style={{ width: '100%', height: '100%', backgroundColor: '#11151c' }} />;

    return (
        <div style={{ width: '100%', height: '100%', overflow: 'hidden' }}>
            <Img
                src={staticFile(src)}
                style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                    transform: `scale(${scale})`,
                }}
            />
        </div>
    );
};

// ─── Hook Intro (first 90 frames = 3 seconds) ─────────────────
const HookIntro: React.FC<{ hookText: string; isShorts: boolean }> = ({ hookText, isShorts }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const opacity = interpolate(frame, [0, 10, 70, 90], [0, 1, 1, 0], { extrapolateRight: 'clamp' });
    const scale = spring({ frame, fps, config: { stiffness: 200, damping: 15 }, durationInFrames: 30 });
    const slideUp = interpolate(frame, [0, 20], [60, 0], { extrapolateRight: 'clamp' });

    return (
        <AbsoluteFill style={{
            zIndex: 20,
            backgroundColor: 'rgba(0,0,0,0.75)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            opacity,
        }}>
            {/* "WAIT" badge */}
            <div style={{
                backgroundColor: '#FF0000',
                color: 'white',
                fontFamily: 'system-ui, sans-serif',
                fontWeight: 900,
                fontSize: isShorts ? '40px' : '48px',
                padding: '10px 30px',
                borderRadius: '50px',
                letterSpacing: '4px',
                marginBottom: '30px',
                transform: `scale(${scale})`,
            }}>⚡ WAIT!</div>

            {/* Hook text */}
            <div style={{
                transform: `translateY(${slideUp}px) scale(${scale})`,
                width: '85%',
                textAlign: 'center',
            }}>
                <h1 style={{
                    fontSize: isShorts ? '68px' : '80px',
                    color: '#FFD700',
                    fontFamily: 'system-ui, sans-serif',
                    fontWeight: 900,
                    textTransform: 'uppercase',
                    lineHeight: 1.2,
                    textShadow: '4px 4px 0 #000, -2px -2px 0 #000',
                    WebkitTextStroke: '2px black',
                    margin: 0,
                }}>{hookText}</h1>
            </div>
        </AbsoluteFill>
    );
};

// ─── Like & Subscribe CTA (last 90 frames = 3 seconds) ────────
const LikeSubscribeCTA: React.FC<{ isShorts: boolean }> = ({ isShorts }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const opacity = interpolate(frame, [0, 15, 75, 90], [0, 1, 1, 0], { extrapolateRight: 'clamp' });
    const scale = spring({ frame, fps, config: { stiffness: 180, damping: 12 }, durationInFrames: 20 });
    // Pulsing bell animation
    const bellRotate = interpolate(
        frame % 20,
        [0, 5, 10, 15, 20],
        [0, 15, 0, -15, 0]
    );

    return (
        <AbsoluteFill style={{
            zIndex: 20,
            backgroundColor: 'rgba(0,0,0,0.82)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            gap: '30px',
            opacity,
        }}>
            <h1 style={{
                fontSize: isShorts ? '55px' : '65px',
                color: 'white',
                fontFamily: 'system-ui, sans-serif',
                fontWeight: 900,
                textAlign: 'center',
                margin: 0,
                transform: `scale(${scale})`,
                textShadow: '3px 3px 0 #000',
            }}>Did you find this helpful?</h1>

            {/* LIKE button */}
            <div style={{
                display: 'flex',
                gap: '40px',
                alignItems: 'center',
                transform: `scale(${scale})`,
            }}>
                <div style={{
                    backgroundColor: '#065FD4',
                    color: 'white',
                    fontFamily: 'system-ui, sans-serif',
                    fontWeight: 900,
                    fontSize: isShorts ? '48px' : '56px',
                    padding: '18px 50px',
                    borderRadius: '50px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '16px',
                    boxShadow: '0 8px 25px rgba(6,95,212,0.6)',
                }}>
                    👍 LIKE
                </div>
                {/* SUBSCRIBE button */}
                <div style={{
                    backgroundColor: '#FF0000',
                    color: 'white',
                    fontFamily: 'system-ui, sans-serif',
                    fontWeight: 900,
                    fontSize: isShorts ? '48px' : '56px',
                    padding: '18px 50px',
                    borderRadius: '50px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '16px',
                    boxShadow: '0 8px 25px rgba(255,0,0,0.6)',
                }}>
                    🔔 SUBSCRIBE
                </div>
            </div>

            <p style={{
                fontSize: isShorts ? '36px' : '42px',
                color: '#aaa',
                fontFamily: 'system-ui, sans-serif',
                fontWeight: 600,
                margin: 0,
                transform: `scale(${scale}) rotate(${bellRotate}deg)`,
            }}>🔔 Hit the bell for daily AI updates!</p>
        </AbsoluteFill>
    );
};

// ─── Main Video ────────────────────────────────────────────────
export const MainVideo: React.FC<MainVideoProps> = ({ slides, audioUrl, bgmUrl, wordTimings, isShorts, hookText, title }) => {
    const { fps, durationInFrames } = useVideoConfig();
    const frame = useCurrentFrame();

    const HOOK_DURATION = 90;     // 3 seconds at 30fps
    const CTA_DURATION = 90;      // 3 seconds at 30fps

    // Prepare hook text
    const finalHookText = hookText || (title ? `${title}` : 'You NEED to know this...');

    // Group words into chunks for captions
    const wordGroups: WordTiming[][] = [];
    if (wordTimings && wordTimings.length > 0) {
        let currentChunk: WordTiming[] = [];
        for (let i = 0; i < wordTimings.length; i++) {
            currentChunk.push(wordTimings[i]);
            const hasPause = i < wordTimings.length - 1 && (wordTimings[i + 1].start - wordTimings[i].end > 0.8);
            if (currentChunk.length >= 4 || hasPause || i === wordTimings.length - 1) {
                wordGroups.push(currentChunk);
                currentChunk = [];
            }
        }
    }

    return (
        <AbsoluteFill style={{ backgroundColor: '#11151c' }}>

            {/* ── Background Visuals ── */}
            {slides && slides.map((slide, idx) => (
                <Sequence
                    key={`bg-${idx}`}
                    from={slide.startFrame}
                    durationInFrames={slide.durationInFrames}
                >
                    <AbsoluteFill style={{ zIndex: 1 }}>
                        {(slide.isVideo && slide.bgPath) ? (
                            <Video src={staticFile(slide.bgPath)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                        ) : (
                            <KenBurnsImage src={slide.bgPath} duration={slide.durationInFrames} />
                        )}
                        {/* Dark overlay */}
                        <div style={{ width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.5)', position: 'absolute' }} />
                    </AbsoluteFill>
                </Sequence>
            ))}

            {/* ── Word-by-Word Captions (BOTTOM position) ── */}
            {wordGroups.map((group, gIdx) => {
                const startFrame = Math.max(0, Math.floor(group[0].start * fps));
                let endFrame = Math.floor(group[group.length - 1].end * fps) + Math.floor(0.2 * fps);
                if (gIdx < wordGroups.length - 1) {
                    endFrame = Math.floor(wordGroups[gIdx + 1][0].start * fps);
                }
                const duration = Math.max(1, endFrame - startFrame);

                return (
                    <Sequence key={`wg-${gIdx}`} from={startFrame} durationInFrames={duration}>
                        <AbsoluteFill style={{
                            zIndex: 10,
                            display: 'flex',
                            justifyContent: 'center',
                            alignItems: 'flex-end',  // ← BOTTOM aligned
                            paddingBottom: isShorts ? '160px' : '120px',
                        }}>
                            <div style={{
                                display: 'flex',
                                flexWrap: 'wrap',
                                justifyContent: 'center',
                                gap: '12px',
                                width: '88%',
                                textAlign: 'center',
                            }}>
                                {group.map((w, wIdx) => {
                                    const wStartF = Math.floor(w.start * fps);
                                    const wEndF = Math.floor(w.end * fps) + Math.floor(0.1 * fps);
                                    const isSpeaking = frame >= wStartF && frame <= wEndF;

                                    const color = isSpeaking ? '#00FF7F' : 'white';
                                    const wordScale = isSpeaking ? '1.12' : '1';
                                    const rotate = isSpeaking ? (wIdx % 2 === 0 ? '-2deg' : '2deg') : '0deg';

                                    return (
                                        <h1 key={wIdx} style={{
                                            fontSize: isShorts ? '65px' : '80px',
                                            color: color,
                                            fontFamily: 'system-ui, sans-serif',
                                            fontWeight: 900,
                                            textTransform: 'uppercase',
                                            margin: 0,
                                            padding: '6px 0',
                                            transform: `scale(${wordScale}) rotate(${rotate})`,
                                            textShadow: '4px 4px 0 #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000',
                                            WebkitTextStroke: '2px black',
                                            transition: 'all 0.1s ease-out',
                                        }}>
                                            {w.word.replace(/[.,!?]/g, '')}
                                        </h1>
                                    );
                                })}
                            </div>
                        </AbsoluteFill>
                    </Sequence>
                );
            })}

            {/* ── Fallback subtitles (no word timings) — BOTTOM ── */}
            {(!wordGroups || wordGroups.length === 0) && slides && slides.map((slide, idx) => (
                <Sequence key={`fallback-txt-${idx}`} from={slide.startFrame} durationInFrames={slide.durationInFrames}>
                    <AbsoluteFill style={{
                        zIndex: 10,
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'flex-end',
                        paddingBottom: isShorts ? '160px' : '120px',
                    }}>
                        <h1 style={{
                            fontSize: isShorts ? '62px' : '72px',
                            color: 'white',
                            fontFamily: 'system-ui, sans-serif',
                            fontWeight: 900,
                            textTransform: 'uppercase',
                            textAlign: 'center',
                            width: '85%',
                            textShadow: '4px 4px 0 #000',
                        }}>{slide.text}</h1>
                    </AbsoluteFill>
                </Sequence>
            ))}

            {/* ── HOOK INTRO (first 3 seconds) ── */}
            <Sequence from={0} durationInFrames={HOOK_DURATION}>
                <HookIntro hookText={finalHookText} isShorts={isShorts} />
            </Sequence>

            {/* ── LIKE & SUBSCRIBE CTA (last 3 seconds) ── */}
            {durationInFrames > CTA_DURATION + HOOK_DURATION && (
                <Sequence from={durationInFrames - CTA_DURATION} durationInFrames={CTA_DURATION}>
                    <LikeSubscribeCTA isShorts={isShorts} />
                </Sequence>
            )}

            {/* ── Audio ── */}
            {audioUrl && <Audio src={staticFile(audioUrl)} />}
            {bgmUrl && <Audio src={staticFile(bgmUrl)} volume={0.15} />}

        </AbsoluteFill>
    );
};
