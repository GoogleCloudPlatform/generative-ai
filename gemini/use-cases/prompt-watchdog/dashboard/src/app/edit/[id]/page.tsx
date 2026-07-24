'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { getPromptAction, updatePromptAction } from '@/app/actions';
import { PromptForm } from '@/components/PromptForm';
import { Navbar } from '@/components/Navbar';
import { CreatePromptInput, Prompt } from '@/types';
import { Loader2 } from 'lucide-react';

export default function EditPromptPage() {
    const router = useRouter();
    const params = useParams();
    const id = params.id as string;

    const [prompt, setPrompt] = useState<Prompt | null>(null);
    const [loading, setLoading] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        if (id) {
            loadPrompt(id);
        }
    }, [id]);

    async function loadPrompt(promptId: string) {
        try {
            const data = await getPromptAction(promptId);
            if (data) {
                setPrompt(data);
            } else {
                router.push('/');
            }
        } catch (e) {
            console.error(e);
            router.push('/');
        } finally {
            setLoading(false);
        }
    }

    const handleSubmit = async (data: CreatePromptInput) => {
        setIsSubmitting(true);
        try {
            await updatePromptAction(id, data);
            router.push('/');
        } catch (e) {
            console.error(e);
            alert('Failed to update prompt');
            setIsSubmitting(false);
        }
    };

    if (loading) {
        return (
            <main className="container">
                <Navbar />
                <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
                    <Loader2 className="animate-spin" size={32} color="var(--text-muted)" />
                </div>
            </main>
        );
    }

    if (!prompt) return null;

    return (
        <main className="container" style={{ paddingBottom: '2rem' }}>
            <Navbar />

            <div style={{ maxWidth: '800px', margin: '0 auto' }}>
                <h1 className="page-title" style={{ fontSize: '2rem' }}>Edit Watchdog Prompt</h1>
                <PromptForm
                    initialValues={{ name: prompt.name, content: prompt.content }}
                    onSubmit={handleSubmit}
                    isSubmitting={isSubmitting}
                />
            </div>
        </main>
    );
}
