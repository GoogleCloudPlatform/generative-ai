# Generative AI Video Evaluator Documentation

**System Version**: 1.3.0  

## 1. Overview
The **Generative AI Video Evaluator** is a high-fidelity quality assurance platform for AI-generated video. It addresses the "hallucination" gap in modern video generation models (Veo, Sora, Kling) by automating the detection of physical, anatomical, and temporal inconsistencies using specialized **ADK Evaluator Agents**.

---

## 2. System Architecture

### Visual Reasoning Pipeline (ADK Agents)
- **Frame Extraction**: Sequential JPEG extraction via HTML5 Canvas.
- **Agent Intelligence**: Parallel execution of specialized sub-agents powered by **Gemini 1.5 Pro**.
- **Agent Roles**: Object Permanence, Physics & Motion, Temporal Consistency.
- **Precision**: Capability to detect exact **start** and **end** times of artifacts.

### Remediation & Regeneration
- **Prompt-to-Prompt Correction**: Automating the conversion of visual failures into corrective generation prompts.
- **Google Veo Integration**: Closed-loop video-to-video regeneration with style consistency references.

---

## 3. The "ADK Agent" Strategy
Evaluating AI-generated video requires a unique "Negative Bias" prompting strategy. Unlike standard AI assistants, these agents are explicitly instructed to be **professionally suspicious**. 

### Code Snippet: Physics Agent Definition
```typescript
// src/lib/agents.ts
physics_motion: {
  type: 'physics_motion',
  systemPrompt: `You are a CRITICAL Physics & Motion Analysis Agent. 
  AI videos often violate basic laws of nature. 
  Rigorously audit physical plausibility. FLAG impossible movements, 
  clipping, and gravity failures.`
}
```

---

## 4. Prompt-to-Prompt Regeneration Logic
When the system detects a visual error (e.g., identity drift), it analyzes the original user prompt to find the root cause and generates a revised prompt for **Google Veo**.

### How it works:
1.  **Map Failures**: Identified issues are mapped to the video timeline.
2.  **Intent Preservation**: **Gemini 1.5 Pro** extracts the creative intent of the original prompt.
3.  **Constraint Injection**: Specific corrective instructions (e.g., "Maintain hand identity through occlusion") are injected into the new prompt.
4.  **Style Reference**: The original video composition is encoded as a STYLE reference for the Veo regeneration call.

---

## 5. Technical Reference

- `src/lib/gemini.ts`: Core API client for ADK Agents.
- `src/lib/remediation.ts`: The prompt-to-prompt regeneration engine.
- `src/lib/agents.ts`: Visual evaluator system prompts.
- `src/lib/veo.ts`: Long-running operation handler for Google Veo.

---

*Copyright © 2026 Generative AI Video Evaluator.*
