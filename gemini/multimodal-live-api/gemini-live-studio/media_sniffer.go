// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import "gemini-live-studio/livebridge"

// SniffedMediaInfo holds container brand, codec strings, and dimensions parsed
// from an ISO BMFF fragmented MP4 chunk.
type SniffedMediaInfo = livebridge.SniffedMediaInfo

// SniffMP4 inspects raw fMP4 data to extract container brand and codec strings.
func SniffMP4(data []byte) SniffedMediaInfo {
	return livebridge.SniffMP4(data)
}

func parseAvc1Dimensions(payload []byte) (width, height int, ok bool) {
	return livebridge.ParseAvc1Dimensions(payload)
}
