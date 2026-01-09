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

import * as React from "react";
import "./sound-wave.css";

export function SoundWave() {
  return (
    <div className="sound-wave-container">
      <svg
        width="190"
        height="55"
        viewBox="40 0 190 55"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <mask id="path-1-inside-1_1500_14453" fill="white">
          <path d="M40 0H230V55H40V0Z" />
        </mask>
        <rect x="41" y="19" width="3" height="17" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="48" y="16" width="3" height="23" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="55" y="22" width="3" height="12" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="62" y="21" width="3" height="14" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="69" y="19" width="3" height="17" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="76" y="17" width="3" height="21" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="83" y="19" width="3" height="18" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="90" y="22" width="3" height="12" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="97" y="25" width="3" height="6" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="104" y="23" width="3" height="9" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="111" y="21" width="3" height="13" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="118" y="18" width="3" height="20" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="125" y="19" width="3" height="18" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="132" y="19" width="3" height="18" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="139" y="22" width="3" height="12" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="146" y="25" width="3" height="6" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="153" y="23" width="3" height="9" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="160" y="21" width="3" height="13" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="167" y="18" width="3" height="20" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="174" y="19" width="3" height="18" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="181" y="19" width="3" height="17" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="188" y="16" width="3" height="23" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="195" y="22" width="3" height="12" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="202" y="21" width="3" height="14" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="209" y="19" width="3" height="17" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="216" y="17" width="3" height="21" rx="1.5" fill="#D9D9D9" className="sound-bar" />
        <rect x="223" y="19" width="3" height="18" rx="1.5" fill="#D9D9D9" className="sound-bar" />
      </svg>
    </div>
  );
}
