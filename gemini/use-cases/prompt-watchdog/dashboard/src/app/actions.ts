// Copyright 2026 Google LLC
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

'use server';

import { firestore } from '@/utils/firestore';
import { Prompt, CreatePromptInput, UpdatePromptInput } from '@/types';
import { DocumentSnapshot, DocumentData } from '@google-cloud/firestore';
import { revalidatePath } from 'next/cache';

// Helper to convert Firestore doc to Prompt
const mapDocToPrompt = (doc: DocumentSnapshot<DocumentData>): Prompt => {
    const data = doc.data();
    if (!data) throw new Error('Document has no data');
    return {
        id: doc.id,
        name: data.name,
        content: data.content,
        serviceUrl: data.serviceUrl,
        status: data.status || 'draft',
        lastDeployedAt: data.lastDeployedAt,
    };
};

export async function getPromptsAction(): Promise<Prompt[]> {
    try {
        const snapshot = await firestore.collection('prompts').get();
        return snapshot.docs.map(doc => mapDocToPrompt(doc));
    } catch (error) {
        console.error('Error fetching prompts from Firestore:', error);
        throw new Error('Failed to fetch prompts');
    }
}

export async function getPromptAction(id: string): Promise<Prompt | undefined> {
    try {
        const doc = await firestore.collection('prompts').doc(id).get();
        if (!doc.exists) return undefined;
        return mapDocToPrompt(doc);
    } catch (error) {
        console.error(`Error fetching prompt ${id}:`, error);
        return undefined;
    }
}

export async function createPromptAction(input: CreatePromptInput): Promise<void> {
    try {
        const newPromptData = {
            name: input.name,
            content: input.content,
            status: 'draft',
            createdAt: new Date().toISOString(),
        };

        await firestore.collection('prompts').add(newPromptData);
    } catch (error) {
        console.error('Error creating prompt:', error);
        throw new Error('Failed to create prompt');
    }

    revalidatePath('/');
}

export async function updatePromptAction(id: string, input: UpdatePromptInput): Promise<void> {
    try {
        await firestore.collection('prompts').doc(id).update({
            ...input,
            updatedAt: new Date().toISOString(),
        });
    } catch (error) {
        console.error(`Error updating prompt ${id}:`, error);
        throw new Error('Failed to update prompt');
    }

    revalidatePath('/');
}


export async function deletePromptAction(id: string): Promise<void> {
    try {
        await firestore.collection('prompts').doc(id).delete();
        revalidatePath('/');
    } catch (error) {
        console.error(`Error deleting prompt ${id}:`, error);
        throw new Error('Failed to delete prompt');
    }
}

export async function deployPromptAction(id: string): Promise<void> {
    try {
        // The runner picks up 'active' prompts from Firestore
        await firestore.collection('prompts').doc(id).update({
            status: 'active',
            lastDeployedAt: new Date().toISOString(),
        });
    } catch (error) {
        console.error(`Error deploying prompt ${id}:`, error);
        throw new Error('Failed to deploy prompt');
    }
}
