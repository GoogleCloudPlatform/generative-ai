// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import { useState } from 'react';
import { AgentConfig, AgentType } from '@/lib/types';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogFooter,
  DialogTrigger 
} from '@/components/ui/dialog';
import { Eye, Zap, Clock, Settings2, Plus, Trash2, Bot } from 'lucide-react';
import { cn } from '@/lib/utils';
import { AGENT_DEFINITIONS } from '@/lib/agents';

interface AgentSettingsProps {
  configs: AgentConfig[];
  onChange: (configs: AgentConfig[]) => void;
  disabled?: boolean;
}

const DEFAULT_ICONS: Record<string, React.ReactNode> = {
  object_permanence: <Eye className="h-4 w-4" />,
  physics_motion: <Zap className="h-4 w-4" />,
  temporal_consistency: <Clock className="h-4 w-4" />,
};

export function AgentSettings({ configs, onChange, disabled }: AgentSettingsProps) {
  const [editingAgent, setEditingAgent] = useState<AgentConfig | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const [newAgent, setNewAgent] = useState<Partial<AgentConfig>>({
    label: '',
    description: '',
    systemPrompt: '',
    enabled: true,
    sensitivity: 70,
    color: 'hsl(var(--primary))',
    icon: 'Bot'
  });

  const updateConfig = (id: string, update: Partial<AgentConfig>) => {
    onChange(configs.map(c => c.id === id ? { ...c, ...update } : c));
  };

  const addAgent = () => {
    if (!newAgent.label) return;
    
    const id = `custom-${Date.now()}`;
    const agent: AgentConfig = {
      id,
      type: newAgent.label.toLowerCase().replace(/\s+/g, '_'),
      enabled: true,
      sensitivity: newAgent.sensitivity || 70,
      label: newAgent.label!,
      description: newAgent.description || '',
      icon: 'Bot',
      color: 'hsl(var(--primary))',
      systemPrompt: newAgent.systemPrompt || `Analyze video frames for ${newAgent.label} issues.`,
    };

    onChange([...configs, agent]);
    setIsAdding(false);
    setNewAgent({
      label: '',
      description: '',
      systemPrompt: '',
      enabled: true,
      sensitivity: 70,
      color: 'hsl(var(--primary))',
      icon: 'Bot'
    });
  };

  const deleteAgent = (id: string) => {
    onChange(configs.filter(c => c.id !== id));
  };

  const saveEdit = () => {
    if (editingAgent) {
      updateConfig(editingAgent.id, editingAgent);
      setEditingAgent(null);
    }
  };

  const getIcon = (config: AgentConfig) => {
    return DEFAULT_ICONS[config.type] || <Bot className="h-4 w-4" />;
  };

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Agent Configuration</h3>
        <Button 
          variant="outline" 
          size="sm" 
          className="h-8 gap-1" 
          onClick={() => setIsAdding(true)}
          disabled={disabled}
        >
          <Plus className="h-3.5 w-3.5" />
          Add Agent
        </Button>
      </div>
      
      <div className="space-y-3">
        {configs.map(config => (
          <div key={config.id} className={cn('space-y-2 pb-3 border-b border-border last:border-0 last:pb-0', !config.enabled && 'opacity-50')}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-primary">{getIcon(config)}</span>
                <div className="flex flex-col">
                  <Label className="text-sm font-medium">{config.label}</Label>
                  <span className="text-[10px] text-muted-foreground line-clamp-1 max-w-[150px]">
                    {config.description}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-muted-foreground hover:text-foreground"
                  onClick={() => setEditingAgent({ ...config })}
                  disabled={disabled}
                >
                  <Settings2 className="h-3.5 w-3.5" />
                </Button>
                <Switch
                  checked={config.enabled}
                  onCheckedChange={(enabled) => updateConfig(config.id, { enabled })}
                  disabled={disabled}
                />
              </div>
            </div>
            {config.enabled && (
              <div className="space-y-1 pl-6">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Sensitivity</span>
                  <span className="font-mono">{config.sensitivity}%</span>
                </div>
                <Slider
                  value={[config.sensitivity]}
                  onValueChange={([v]) => updateConfig(config.id, { sensitivity: v })}
                  min={10}
                  max={100}
                  step={5}
                  disabled={disabled}
                  className="w-full"
                />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Edit Agent Dialog */}
      <Dialog open={!!editingAgent} onOpenChange={(open) => !open && setEditingAgent(null)}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Edit Agent: {editingAgent?.label}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Label</Label>
              <Input 
                value={editingAgent?.label || ''} 
                onChange={e => setEditingAgent(prev => prev ? { ...prev, label: e.target.value } : null)}
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input 
                value={editingAgent?.description || ''} 
                onChange={e => setEditingAgent(prev => prev ? { ...prev, description: e.target.value } : null)}
              />
            </div>
            <div className="space-y-2">
              <Label>System Prompt</Label>
              <Textarea 
                className="min-h-[150px] font-mono text-xs"
                value={editingAgent?.systemPrompt || (editingAgent ? AGENT_DEFINITIONS[editingAgent.type as any]?.systemPrompt : '') || ''} 
                placeholder="Enter the instructions for this AI agent..."
                onChange={e => setEditingAgent(prev => prev ? { ...prev, systemPrompt: e.target.value } : null)}
              />
              <p className="text-[10px] text-muted-foreground italic">
                Note: Editing the prompt will change how the AI identifies issues for this agent.
              </p>
            </div>
          </div>
          <DialogFooter className="flex justify-between sm:justify-between items-center">
            {editingAgent && !DEFAULT_ICONS[editingAgent.type] && (
              <Button 
                variant="destructive" 
                size="sm" 
                onClick={() => {
                  deleteAgent(editingAgent.id);
                  setEditingAgent(null);
                }}
              >
                <Trash2 className="h-3.5 w-3.5 mr-1" />
                Delete Agent
              </Button>
            )}
            <div className="flex gap-2 ml-auto">
              <Button variant="outline" onClick={() => setEditingAgent(null)}>Cancel</Button>
              <Button onClick={saveEdit}>Save Changes</Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Agent Dialog */}
      <Dialog open={isAdding} onOpenChange={setIsAdding}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Add New Agent</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Agent Name</Label>
              <Input 
                placeholder="e.g., Audio Quality"
                value={newAgent.label} 
                onChange={e => setNewAgent(prev => ({ ...prev, label: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input 
                placeholder="What does this agent look for?"
                value={newAgent.description} 
                onChange={e => setNewAgent(prev => ({ ...prev, description: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>System Prompt</Label>
              <Textarea 
                className="min-h-[150px] font-mono text-xs"
                placeholder="Instructions for the AI..."
                value={newAgent.systemPrompt} 
                onChange={e => setNewAgent(prev => ({ ...prev, systemPrompt: e.target.value }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAdding(false)}>Cancel</Button>
            <Button onClick={addAgent} disabled={!newAgent.label}>Create Agent</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
