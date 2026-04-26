import React from 'react';

export default function PlaybackControls({
  totalLogs,
  playbackIndex,
  setPlaybackIndex,
  isPlaying,
  setIsPlaying,
  speed,
  setSpeed,
}) {
  const isAtEnd = playbackIndex >= totalLogs;
  const isAtStart = playbackIndex === 0;
  const progress = totalLogs > 0 ? (playbackIndex / totalLogs) * 100 : 0;

  const handlePlayPause = () => {
    if (isAtEnd && !isPlaying) {
      setPlaybackIndex(0);
      setIsPlaying(true);
    } else {
      setIsPlaying(!isPlaying);
    }
  };

  return (
    <div className="card" style={{ padding: '16px', position: 'relative', overflow: 'hidden' }}>
      {/* ── Progress bar ── */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '4px', background: 'rgba(255,255,255,0.05)' }}>
        <div
          style={{ 
            height: '100%', 
            width: `${progress}%`, 
            background: 'var(--gradient-primary)', 
            transition: 'width 0.3s ease-out',
            boxShadow: '0 0 10px rgba(208, 149, 255, 0.4)'
          }}
        />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* ── Header ── */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ fontSize: '10px', fontWeight: '900', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', margin: 0 }}>
            Playback Control
          </h2>
          <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'white', background: 'rgba(0,0,0,0.3)', padding: '4px 10px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
            {playbackIndex} <span style={{ opacity: 0.3 }}>/</span> {totalLogs}
          </div>
        </div>

        {/* ── Controls ── */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
               disabled={isAtStart}
               onClick={() => { setIsPlaying(false); setPlaybackIndex(Math.max(0, playbackIndex - 1)); }}
               style={{ 
                 width: '32px', height: '32px', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', 
                 border: '1px solid var(--border-subtle)', color: 'white', cursor: 'pointer',
                 opacity: isAtStart ? 0.3 : 1
               }}
            >⏮</button>

            <button
               onClick={handlePlayPause}
               disabled={totalLogs === 0}
               style={{ 
                 width: '40px', height: '32px', borderRadius: '6px', 
                 background: isPlaying ? 'rgba(208, 149, 255, 0.2)' : 'rgba(255,255,255,0.1)', 
                 border: `1px solid ${isPlaying ? 'var(--color-ceo)' : 'var(--border-subtle)'}`, 
                 color: isPlaying ? 'var(--color-ceo)' : 'white', cursor: 'pointer'
               }}
            >
              {isPlaying ? '⏸' : '▶'}
            </button>

            <button
               disabled={isAtEnd}
               onClick={() => { setIsPlaying(false); setPlaybackIndex(Math.min(totalLogs, playbackIndex + 1)); }}
               style={{ 
                 width: '32px', height: '32px', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', 
                 border: '1px solid var(--border-subtle)', color: 'white', cursor: 'pointer',
                 opacity: isAtEnd ? 0.3 : 1
               }}
            >⏭</button>
          </div>

          <div style={{ display: 'flex', background: 'rgba(0,0,0,0.2)', borderRadius: '6px', border: '1px solid var(--border-subtle)', overflow: 'hidden' }}>
            {[0.5, 1, 2].map((s) => (
              <button
                key={s}
                onClick={() => setSpeed(s)}
                style={{ 
                  padding: '4px 10px', fontSize: '10px', fontWeight: '800', border: 'none', borderRight: '1px solid var(--border-subtle)',
                  background: speed === s ? 'rgba(208, 149, 255, 0.1)' : 'transparent',
                  color: speed === s ? 'var(--color-ceo)' : 'var(--text-muted)',
                  cursor: 'pointer'
                }}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>

        {/* ── Slider ── */}
        <input
          type="range"
          min="0"
          max={totalLogs}
          value={playbackIndex}
          onChange={(e) => { setIsPlaying(false); setPlaybackIndex(Number(e.target.value)); }}
          style={{ width: '100%', cursor: 'pointer', accentColor: 'var(--color-ceo)' }}
        />
      </div>
    </div>
  );
}
