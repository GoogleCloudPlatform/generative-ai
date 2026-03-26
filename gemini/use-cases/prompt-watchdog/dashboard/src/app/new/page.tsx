'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createPromptAction } from '@/app/actions';
import { PromptForm } from '@/components/PromptForm';
import { Navbar } from '@/components/Navbar';
import { CreatePromptInput } from '@/types';

export default function NewPromptPage() {
    const router = useRouter();
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (data: CreatePromptInput) => {
        setIsSubmitting(true);
        try {
            await createPromptAction(data);
            router.push('/');
        } catch (e) {
            console.error(e);
            alert('Failed to create prompt');
            setIsSubmitting(false); // Only set to false on error, success redirects away
        }
    };

    return (
        <main className="container" style={{ paddingBottom: '2rem' }}>
            <Navbar />

            <div style={{ maxWidth: '800px', margin: '0 auto' }}>
                <h1 className="page-title" style={{ fontSize: '2rem' }}>New Watchdog Prompt</h1>
                <PromptForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
            </div>
        </main>
    );
}
