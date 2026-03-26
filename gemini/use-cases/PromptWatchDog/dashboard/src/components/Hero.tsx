'use client';

import Image from 'next/image';

export function Hero() {
    return (
        <div style={{
            marginBottom: '2rem',
            padding: '3rem 1rem',
            background: 'linear-gradient(to bottom, #f8faff, #ffffff)', // Very subtle top-down gradient
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-color)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center',
            position: 'relative',
            overflow: 'hidden'
        }}>

            <div style={{
                position: 'relative',
                zIndex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '1rem'
            }}>
                {/* Logo in White Circle */}
                <div style={{
                    marginBottom: '1rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                }}>
                    <Image src="/logo2.png" alt="WatchDog Logo" width={100} height={100} style={{ objectFit: 'contain' }} />
                </div>

                <h1 style={{
                    fontSize: '2.5rem',
                    fontWeight: 700,
                    color: 'var(--text-main)',
                    margin: 0,
                    letterSpacing: '-0.02em'
                }}>
                    PromptWatchDog
                </h1>

                <p style={{
                    fontSize: '1.1rem',
                    color: 'var(--text-muted)',
                    maxWidth: '600px',
                    margin: 0
                }}>
                    Real-time Insights metric powered by Gemini
                </p>
            </div>
        </div>
    );
}
