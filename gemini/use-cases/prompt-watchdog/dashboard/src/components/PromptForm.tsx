'use client';

import { useState } from 'react';
import { CreatePromptInput } from '@/types';
import { Loader2, Save } from 'lucide-react';
import Link from 'next/link';

interface PromptFormProps {
    initialValues?: CreatePromptInput;
    onSubmit: (data: CreatePromptInput) => Promise<void>;
    isSubmitting?: boolean;
}

export function PromptForm({ initialValues, onSubmit, isSubmitting }: PromptFormProps) {
    const [name, setName] = useState(initialValues?.name || '');
    const [content, setContent] = useState(initialValues?.content || '');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSubmit({ name, content });
    };

    return (
        <form onSubmit={handleSubmit} className="glass-panel" style={{
            padding: '2rem',
            background: 'white',
            border: '1px solid var(--border-color)',
            boxShadow: 'var(--shadow-sm)'
        }}>
            <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, color: 'var(--text-main)', fontSize: '0.9rem' }} htmlFor="name">
                    Prompt Name
                </label>
                <input
                    id="name"
                    type="text"
                    className="input-field"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Customer Service Bot"
                    required
                    autoFocus
                    style={{ background: '#f8f9fa' }}
                />
            </div>

            <div style={{ marginBottom: '2rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, color: 'var(--text-main)', fontSize: '0.9rem' }} htmlFor="content">
                    System Prompt
                </label>
                <textarea
                    id="content"
                    className="input-field"
                    style={{
                        minHeight: '300px',
                        fontFamily: 'robotomono, monospace',
                        lineHeight: '1.6',
                        background: '#f8f9fa'
                    }}
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="Enter the system prompt here..."
                    required
                />
                <p style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    This prompt will be configured in the watchdog service.
                </p>
            </div>

            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', paddingTop: '1.5rem', borderTop: '1px solid var(--border-color)' }}>
                <Link href="/" className="btn btn-secondary" style={{ boxShadow: 'none' }}>
                    Cancel
                </Link>
                <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                    {isSubmitting ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
                    {isSubmitting ? 'Saving...' : 'Save Prompt'}
                </button>
            </div>
        </form>
    );
}
