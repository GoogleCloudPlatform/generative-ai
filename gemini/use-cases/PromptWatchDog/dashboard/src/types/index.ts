export interface Prompt {
    id: string;
    name: string;
    content: string;
    serviceUrl?: string; // e.g. https://watchdog-my-prompt-xyz.run.app
    status: 'draft' | 'deploying' | 'active' | 'failed';
    lastDeployedAt?: string;
}

export type CreatePromptInput = Pick<Prompt, 'name' | 'content'>;
export type UpdatePromptInput = Partial<CreatePromptInput>;
