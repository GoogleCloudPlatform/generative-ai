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

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"strings"
)

// SniffedMediaInfo holds information extracted from binary MP4 fragments.
type SniffedMediaInfo struct {
	MajorBrand       string
	CompatibleBrands []string
	Codecs           []string
	SuggestedMime    string
	// Width/Height are the coded video dimensions in pixels, read from the
	// avc1 VisualSampleEntry inside stsd. Zero if no video sample entry was
	// found (e.g. audio-only fragment, or the entry didn't fit in this
	// fragment's byte range).
	Width, Height int
}

// SniffMP4 inspects raw fMP4 data to extract container brand and codec strings.
func SniffMP4(data []byte) SniffedMediaInfo {
	info := SniffedMediaInfo{}
	if len(data) < 8 {
		return info
	}

	buf := bytes.NewReader(data)
	for buf.Len() >= 8 {
		var boxSize uint32
		var boxType [4]byte

		if err := binary.Read(buf, binary.BigEndian, &boxSize); err != nil {
			break
		}
		if err := binary.Read(buf, binary.BigEndian, &boxType); err != nil {
			break
		}

		typeStr := string(boxType[:])
		payloadSize := int(boxSize) - 8
		if boxSize == 1 { // 64-bit size
			var extSize uint64
			if err := binary.Read(buf, binary.BigEndian, &extSize); err != nil {
				break
			}
			payloadSize = int(extSize) - 16
		} else if boxSize == 0 { // extends to EOF
			payloadSize = buf.Len()
		}

		if payloadSize < 0 || payloadSize > buf.Len() {
			break
		}

		boxPayload := make([]byte, payloadSize)
		if n, _ := buf.Read(boxPayload); n < payloadSize {
			break
		}

		switch typeStr {
		case "ftyp":
			parseFtyp(boxPayload, &info)
		case "moov", "trak", "mdia", "minf", "stbl", "stsd":
			parseRecursiveBoxes(boxPayload, &info)
		}
	}

	if len(info.Codecs) > 0 {
		info.SuggestedMime = fmt.Sprintf("video/mp4; codecs=\"%s\"", strings.Join(info.Codecs, ", "))
	} else if info.MajorBrand != "" {
		info.SuggestedMime = "video/mp4"
	}

	return info
}

func parseFtyp(payload []byte, info *SniffedMediaInfo) {
	if len(payload) < 8 {
		return
	}
	info.MajorBrand = string(payload[0:4])
	for i := 8; i+4 <= len(payload); i += 4 {
		brand := string(payload[i : i+4])
		info.CompatibleBrands = append(info.CompatibleBrands, brand)
	}
}

func parseRecursiveBoxes(payload []byte, info *SniffedMediaInfo) {
	if bytes.Contains(payload, []byte("avc1")) {
		addCodec(info, parseAvc1Codec(payload))
		if w, h, ok := parseAvc1Dimensions(payload); ok {
			info.Width, info.Height = w, h
		}
	}
	if bytes.Contains(payload, []byte("hvc1")) || bytes.Contains(payload, []byte("hev1")) {
		addCodec(info, "hvc1.1.6.L93.B0")
	}
	if bytes.Contains(payload, []byte("mp4a")) {
		addCodec(info, "mp4a.40.2")
	}
	if bytes.Contains(payload, []byte("Opus")) {
		addCodec(info, "opus")
	}
	if bytes.Contains(payload, []byte("vp09")) {
		addCodec(info, "vp09.00.41.08")
	}
}

func parseAvc1Codec(payload []byte) string {
	idx := bytes.Index(payload, []byte("avcC"))
	if idx != -1 && idx+7 < len(payload) {
		profile := payload[idx+5]
		compat := payload[idx+6]
		level := payload[idx+7]
		return fmt.Sprintf("avc1.%02X%02X%02X", profile, compat, level)
	}
	return "avc1.42C020" // Gemini 3.5 / 3.8 default Baseline Profile Level 3.2
}

// parseAvc1Dimensions reads the coded width/height out of an avc1
// VisualSampleEntry. Layout after the "avc1" type field (ISO/IEC 14496-12):
//
//	reserved[6] + data_reference_index[2] + pre_defined[2] + reserved[2] +
//	pre_defined[3*4=12] + width[2] + height[2] + ...
//
// bytes.Index finds the start of the ASCII "avc1" type bytes, so the fields
// above begin 4 bytes later (right after the type field itself).
func parseAvc1Dimensions(payload []byte) (width, height int, ok bool) {
	idx := bytes.Index(payload, []byte("avc1"))
	if idx == -1 {
		return 0, 0, false
	}
	widthOff := idx + 4 + 6 + 2 + 2 + 2 + 12
	if widthOff+4 > len(payload) {
		return 0, 0, false
	}
	w := binary.BigEndian.Uint16(payload[widthOff : widthOff+2])
	h := binary.BigEndian.Uint16(payload[widthOff+2 : widthOff+4])
	if w == 0 || h == 0 {
		return 0, 0, false
	}
	return int(w), int(h), true
}

func addCodec(info *SniffedMediaInfo, codec string) {
	for _, c := range info.Codecs {
		if c == codec {
			return
		}
	}
	info.Codecs = append(info.Codecs, codec)
}
