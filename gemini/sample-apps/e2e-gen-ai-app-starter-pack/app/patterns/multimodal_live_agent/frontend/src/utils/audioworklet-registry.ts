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

/**
 * A registry to map attached worklets by their audio-context
 * any module using `audioContext.audioWorklet.addModule(` should register the worklet here
 */
export type WorkletGraph = {
  node?: AudioWorkletNode;
  handlers: Array<(this: MessagePort, ev: MessageEvent) => any>;
};

export const registeredWorklets: Map<
  AudioContext,
  Record<string, WorkletGraph>
> = new Map();

export const createWorketFromSrc = (
  workletName: string,
  workletSrc: string,
) => {
  const script = new Blob(
    [`registerProcessor("${workletName}", ${workletSrc})`],
    {
      type: "application/javascript",
    },
  );

  return URL.createObjectURL(script);
};
