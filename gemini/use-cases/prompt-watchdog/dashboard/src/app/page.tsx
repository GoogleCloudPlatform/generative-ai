'use client';

import { useEffect, useState } from 'react';
import { Prompt } from '@/types';
import { getPromptsAction, deletePromptAction, deployPromptAction } from '@/app/actions';
import { PromptCard } from '@/components/PromptCard';
import { Hero } from '@/components/Hero';
import { Navbar } from '@/components/Navbar';
import { Loader2 } from 'lucide-react';

export default function Dashboard() {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPrompts();
  }, []);

  async function loadPrompts() {
    try {
      const data = await getPromptsAction();
      setPrompts(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    if (confirm('Are you sure you want to delete this prompt?')) {
      await deletePromptAction(id);
      await loadPrompts();
    }
  }

  async function handleDeploy(id: string) {
    // Optimistic UI or just wait for reload
    // In a real app we might want to show a toast
    await deployPromptAction(id);
    await loadPrompts();
  }

  return (
    <main className="container" style={{ paddingBottom: '3rem' }}>
      <Navbar />

      <Hero />

      <div id="prompts-list" style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--text-main)' }}>Deployed Prompts</h2>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
          <Loader2 className="animate-spin" size={32} color="var(--primary-color)" />
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1.5rem' }}>
          {prompts.map(prompt => (
            <PromptCard key={prompt.id} prompt={prompt} onDelete={handleDelete} onDeploy={handleDeploy} />
          ))}

          {prompts.length === 0 && (
            <div className="glass-panel" style={{
              gridColumn: '1 / -1',
              padding: '4rem',
              textAlign: 'center',
              color: 'var(--text-muted)',
              background: 'white'
            }}>
              <p>No prompts deployed yet. Create one to get started.</p>
            </div>
          )}
        </div>
      )}
    </main>
  );
}
