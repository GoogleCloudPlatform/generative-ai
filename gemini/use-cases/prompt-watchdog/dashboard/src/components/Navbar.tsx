import Link from 'next/link';
import { Terminal, ShieldCheck } from 'lucide-react';
import Image from 'next/image';

export function Navbar() {
    return (
        <nav className="glass-panel" style={{
            marginBottom: '2rem',
            padding: '0.75rem 1.5rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderRadius: '0 0 var(--radius-md) var(--radius-md)',
            marginTop: '-1px',
            borderTop: 'none',
            background: 'white',
            borderBottom: '1px solid var(--border-color)',
            boxShadow: '0 1px 2px 0 rgba(60,64,67,0.3)'
        }}>
            <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--primary-color)'
                }}>
                    <Image src="/logo2.png" alt="Logo" width={40} height={40} style={{ objectFit: 'contain' }} />
                </div>
                <span style={{ fontSize: '1.35rem', fontWeight: 500, letterSpacing: '-0.5px', color: '#5f6368' }}>
                    Prompt<span style={{ color: 'var(--primary-color)', fontWeight: 600 }}>WatchDog</span>
                </span>
            </Link>

            <div style={{ display: 'flex', gap: '1rem' }}>
                <Link href="/new" className="btn btn-primary" style={{ boxShadow: 'none' }}>
                    <Terminal size={18} />
                    <span style={{ marginLeft: '4px' }}>New Prompt</span>
                </Link>
            </div>
        </nav>
    );
}
