'use client';

import { Prompt } from '@/types';
import { ExternalLink, Edit, Trash2, Clock, Rocket, Copy } from 'lucide-react';
import Link from 'next/link';

interface PromptCardProps {
    prompt: Prompt;
    onDelete: (id: string) => void;
    onDeploy: (id: string) => void;
}

export function PromptCard({ prompt, onDelete, onDeploy }: PromptCardProps) {
    const isDeploying = prompt.status === 'deploying';

    const statusConfig = {
        active: { class: 'badge-success', label: 'Active' },
        deploying: { class: 'badge-warning', label: 'Deploying...' },
        failed: { class: 'badge-error', label: 'Failed' },
        draft: { class: 'badge-neutral', label: 'Draft' }
    }[prompt.status];

    // Simple copy to clipboard function
    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
    };

    return (
        <div className="glass-panel" style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
            transition: 'all 0.2s cubic-bezier(0.4, 0.0, 0.2, 1)',
            position: 'relative',
            overflow: 'hidden',
            background: 'white',
            border: '1px solid var(--border-color)',
        }}>
            {/* Card Header with Status Accent */}
            <div style={{ padding: '1.5rem 1.5rem 0', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                        <h3 style={{ fontSize: '1.25rem', fontWeight: 500, color: 'var(--text-main)', margin: 0 }}>{prompt.name}</h3>
                        <span className={`badge ${statusConfig.class}`}>
                            {statusConfig.label}
                        </span>
                    </div>
                    {prompt.status === 'active' && prompt.serviceUrl && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            <span style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {prompt.serviceUrl.replace('https://', '')}
                            </span>
                            <button onClick={() => copyToClipboard(prompt.serviceUrl!)} title="Copy URL" style={{ cursor: 'pointer', color: 'var(--primary-color)' }}>
                                <Copy size={12} />
                            </button>
                        </div>
                    )}
                </div>

                <div style={{ display: 'flex', gap: '0.25rem' }}>
                    <Link href={`/edit/${prompt.id}`} className="btn btn-secondary" style={{ padding: '0.4rem', border: 'none', background: 'transparent' }} title="Edit">
                        <Edit size={18} color="var(--text-muted)" />
                    </Link>
                    <button
                        onClick={() => onDelete(prompt.id)}
                        className="btn btn-secondary"
                        style={{ padding: '0.4rem', color: 'var(--text-muted)', border: 'none', background: 'transparent' }}
                        title="Delete"
                    >
                        <Trash2 size={18} />
                    </button>
                </div>
            </div>

            {/* Content Preview */}
            <div style={{ padding: '0 1.5rem' }}>
                <div className="code-preview" style={{
                    maxHeight: '120px',
                    display: '-webkit-box',
                    WebkitLineClamp: 4,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                }}>
                    {prompt.content}
                    {/* Add a fade effect at the bottom if content is long? CSS limitation for pure clamp, but looks okay */}
                </div>
            </div>

            {/* Footer Actions */}
            <div style={{
                marginTop: 'auto',
                padding: '1rem 1.5rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                borderTop: '1px solid var(--bg-app)',
                background: '#ffffff'
            }}>

                {prompt.lastDeployedAt ? (
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                        <Clock size={12} />
                        {new Date(prompt.lastDeployedAt).toLocaleDateString()}
                    </span>
                ) : <span></span>}

                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                    {prompt.status === 'active' && prompt.serviceUrl && (
                        <a
                            href={prompt.serviceUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--primary-color)', fontWeight: 500 }}
                        >
                            Visit <ExternalLink size={14} />
                        </a>
                    )}

                    <button
                        onClick={() => onDeploy(prompt.id)}
                        className="btn"
                        disabled={isDeploying}
                        style={{
                            background: isDeploying ? 'var(--bg-surface-hover)' : 'var(--primary-color)',
                            color: isDeploying ? 'var(--text-muted)' : 'white',
                            padding: '0.4rem 0.8rem',
                            fontSize: '0.8rem',
                            borderRadius: '4px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.4rem'
                        }}
                    >
                        {isDeploying ? <Clock size={14} className="animate-spin" /> : <Rocket size={14} />}
                        {isDeploying ? 'Deploying' : 'Deploy'}
                    </button>
                </div>
            </div>
        </div>
    );
}
