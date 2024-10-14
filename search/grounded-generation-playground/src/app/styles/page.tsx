/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Slider } from '@/components/ui/slider';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import * as Accordion from '@radix-ui/react-accordion';

import {
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
  AccordionDemo,
} from '@/components/ui/accordion';

// import { ChevronDownIcon } from "@radix-ui/react-icons";

export default function StylesPage() {
  return (
    <div className="min-h-screen bg-black text-white font-sans">
      <div className="container mx-auto p-8 bg-background text-foreground min-h-screen">
        <h1 className="text-4xl font-bold mb-8">Style Showcase</h1>
        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-4">Colors</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { name: 'Background', class: 'bg-background' },
              { name: 'Foreground', class: 'bg-foreground text-background' },
              { name: 'Card', class: 'bg-card' },
              {
                name: 'Card Foreground',
                class: 'bg-card-foreground text-background',
              },
              { name: 'Popover', class: 'bg-popover' },
              {
                name: 'Popover Foreground',
                class: 'bg-popover-foreground text-background',
              },
              { name: 'Primary', class: 'bg-primary text-primary-foreground' },
              {
                name: 'Secondary',
                class: 'bg-secondary text-secondary-foreground',
              },
              { name: 'Muted', class: 'bg-muted text-muted-foreground' },
              { name: 'Accent', class: 'bg-accent text-accent-foreground' },
              {
                name: 'Destructive',
                class: 'bg-destructive text-destructive-foreground',
              },
            ].map((color) => (
              <div
                key={color.name}
                className={`p-4 border border-border rounded ${color.class}`}
              >
                {color.name}
              </div>
            ))}
          </div>
        </section>
        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-4">Typography</h2>
          <div className="space-y-2">
            <h1 className="text-4xl font-bold">Heading 1</h1>
            <h2 className="text-3xl font-semibold">Heading 2</h2>
            <h3 className="text-2xl font-medium">Heading 3</h3>
            <p className="text-base">Regular paragraph text</p>
            <p className="text-sm">Small text</p>
            <p className="text-xs">Extra small text</p>
          </div>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-4">Card Variants</h2>
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Default Card</CardTitle>
                <CardDescription>This is the default card style</CardDescription>
              </CardHeader>
              <CardContent>Default card content</CardContent>
            </Card>

            <Card className={cn('card-user')}>
              <CardHeader>
                <CardTitle>User Card</CardTitle>
                <CardDescription>This card uses the user style</CardDescription>
              </CardHeader>
              <CardContent>User card content</CardContent>
            </Card>

            <Card className={cn('card-system')}>
              <CardHeader>
                <CardTitle>System Card</CardTitle>
                <CardDescription>This card uses the system style</CardDescription>
              </CardHeader>
              <CardContent>System card content</CardContent>
            </Card>
          </div>
        </section>
        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-4">Accordions</h2>
          <AccordionDemo />
          <hr />
          <Accordion.Root
            className="AccordionRoot"
            type="single"
            defaultValue="item-1"
            collapsible
          >
            <AccordionItem value="item-1">
              <AccordionTrigger>Custom</AccordionTrigger>
              <AccordionContent>
                Basic 2nd accordion direct implementation.
              </AccordionContent>
            </AccordionItem>
          </Accordion.Root>

          <Card className={cn('card-user')}>
            <CardHeader>
              <CardTitle>Card with Accordion</CardTitle>
            </CardHeader>
            <CardContent>
              User card content.
              <AccordionDemo />
              More card content.
            </CardContent>
          </Card>

          <Card className={cn('card-system')}>
            <CardHeader>
              <CardTitle>System Card</CardTitle>
              <CardDescription>This card uses the system style</CardDescription>
            </CardHeader>
            <CardContent>System card content</CardContent>
          </Card>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-4">Components</h2>

          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Card Title</CardTitle>
              </CardHeader>
              <CardContent>This is a card component.</CardContent>
            </Card>

            <Button>Default Button</Button>
            <Button variant="destructive">Destructive Button</Button>
            <Button variant="outline">Outline Button</Button>
            <Button variant="secondary">Secondary Button</Button>
            <Button variant="ghost">Ghost Button</Button>
            <Button variant="link">Link Button</Button>

            <Input placeholder="Input field" />

            <Slider defaultValue={[50]} max={100} step={1} />

            <Tabs defaultValue="tab1">
              <TabsList>
                <TabsTrigger value="tab1">Tab 1</TabsTrigger>
                <TabsTrigger value="tab2">Tab 2</TabsTrigger>
              </TabsList>
              <TabsContent value="tab1">Content of Tab 1</TabsContent>
              <TabsContent value="tab2">Content of Tab 2</TabsContent>
            </Tabs>
          </div>
        </section>
      </div>
    </div>
  );
}
