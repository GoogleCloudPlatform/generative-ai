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

// accordion.tsx
"use client";

import React from "react";
import * as AccordionPrimitive from "@radix-ui/react-accordion";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

const Accordion = React.forwardRef<
  React.ElementRef<typeof AccordionPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof AccordionPrimitive.Root>
>(({ className, ...props }, ref) => (
  <AccordionPrimitive.Root
    ref={ref}
    className={cn(
      "rounded-md border border-[--accordion-border-color] bg-[--accordion-bg-color] shadow-sm",
      className,
    )}
    {...props}
  />
));
Accordion.displayName = "Accordion";

const accordion-item = React.forwardRef<
  React.ElementRef<typeof AccordionPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof AccordionPrimitive.Item>
>(({ className, ...props }, ref) => (
  <AccordionPrimitive.Item
    ref={ref}
    className={cn(
      "border-b border-[--accordion-border-color] last:border-0",
      className,
    )}
    {...props}
  />
));
accordion-item.displayName = "accordion-item";

const accordion-trigger = React.forwardRef<
  React.ElementRef<typeof AccordionPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof AccordionPrimitive.Trigger>
>(({ className, children, ...props }, ref) => (
  <AccordionPrimitive.Header className="flex">
    <AccordionPrimitive.Trigger
      ref={ref}
      className={cn(
        "flex flex-1 items-center justify-between px-4 py-4 font-medium transition-all hover:bg-[--accordion-hover-bg-color] [&[data-state=open]>svg]:rotate-180",
        "text-[--accordion-text-color]",
        className,
      )}
      {...props}
    >
      {children}
      <ChevronDown className="h-4 w-4 shrink-0 transition-transform duration-200" />
    </AccordionPrimitive.Trigger>
  </AccordionPrimitive.Header>
));
accordion-trigger.displayName = "accordion-trigger";

const accordion-content = React.forwardRef<
  React.ElementRef<typeof AccordionPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof AccordionPrimitive.Content>
>(({ className, children, ...props }, ref) => (
  <AccordionPrimitive.Content
    ref={ref}
    className={cn(
      "overflow-hidden text-sm transition-all data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down",
      "bg-[--accordion-content-bg-color] text-[--accordion-text-color]",
      className,
    )}
    {...props}
  >
    <div className="px-4 pb-4 pt-0">{children}</div>
  </AccordionPrimitive.Content>
));
accordion-content.displayName = "accordion-content";

const AccordionDemo = () => (
  <AccordionPrimitive.Root
    className="accordion-root w-full"
    type="single"
    defaultValue="item-1"
    collapsible
  >
    <accordion-item className="accordion-item" value="item-1">
      <accordion-trigger>Is it accessible?</accordion-trigger>
      <accordion-content>
        Yes. It adheres to the WAI-ARIA design pattern.
      </accordion-content>
    </accordion-item>

    <accordion-item className="accordion-item" value="item-2">
      <accordion-trigger>Is it unstyled?</accordion-trigger>
      <accordion-content>
        Yes. It's unstyled by default, giving you freedom over the look and
        feel.
      </accordion-content>
    </accordion-item>

    <accordion-item className="accordion-item" value="item-3">
      <accordion-trigger>Can it be animated?</accordion-trigger>
      <accordion-content className="accordion-content">
        <div className="accordion-contentText">
          Yes! You can animate the Accordion with CSS or JavaScript.
        </div>
      </accordion-content>
    </accordion-item>
  </AccordionPrimitive.Root>
);

export {
  Accordion,
  accordion-item,
  accordion-trigger,
  accordion-content,
  AccordionDemo,
};
