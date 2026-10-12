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
	"slices"
	"testing"
)

func makeBox(boxType string, payload []byte) []byte {
	var buf bytes.Buffer
	_ = binary.Write(&buf, binary.BigEndian, uint32(8+len(payload)))
	buf.WriteString(boxType)
	buf.Write(payload)
	return buf.Bytes()
}

func makeAvc1Payload(width, height uint16, profile, compat, level byte, includeAvcC bool) []byte {
	var buf bytes.Buffer
	buf.WriteString("avc1")
	// reserved[6] + data_reference_index[2] + pre_defined[2] + reserved[2] + pre_defined[12] = 24 bytes
	buf.Write(make([]byte, 24))
	_ = binary.Write(&buf, binary.BigEndian, width)
	_ = binary.Write(&buf, binary.BigEndian, height)
	if includeAvcC {
		// avcC box: "avcC" + configurationVersion(1) + profile + compat + level
		buf.WriteString("avcC")
		buf.Write([]byte{0x01, profile, compat, level, 0xFF})
	}
	return buf.Bytes()
}

func TestSniffMP4_FullFragment(t *testing.T) {
	// ftyp payload: major_brand(4) + minor_version(4) + compatible_brands...
	ftypPayload := []byte("iso5\x00\x00\x02\x00iso5mp41")
	ftypBox := makeBox("ftyp", ftypPayload)

	var moovPayload bytes.Buffer
	moovPayload.Write(makeAvc1Payload(704, 1280, 0x42, 0xC0, 0x20, true))
	moovPayload.WriteString("mp4a")
	moovBox := makeBox("moov", moovPayload.Bytes())

	fragment := append(ftypBox, moovBox...)
	got := SniffMP4(fragment)

	if got.MajorBrand != "iso5" {
		t.Errorf("MajorBrand = %q, want iso5", got.MajorBrand)
	}
	wantBrands := []string{"iso5", "mp41"}
	if !slices.Equal(got.CompatibleBrands, wantBrands) {
		t.Errorf("CompatibleBrands = %v, want %v", got.CompatibleBrands, wantBrands)
	}
	wantCodecs := []string{"avc1.42C020", "mp4a.40.2"}
	if !slices.Equal(got.Codecs, wantCodecs) {
		t.Errorf("Codecs = %v, want %v", got.Codecs, wantCodecs)
	}
	wantMime := `video/mp4; codecs="avc1.42C020, mp4a.40.2"`
	if got.SuggestedMime != wantMime {
		t.Errorf("SuggestedMime = %q, want %q", got.SuggestedMime, wantMime)
	}
	if got.Width != 704 || got.Height != 1280 {
		t.Errorf("dimensions = %dx%d, want 704x1280", got.Width, got.Height)
	}
}

func TestSniffMP4_EdgeCasesAndFallbacks(t *testing.T) {
	if got := SniffMP4([]byte("short")); got.SuggestedMime != "" || len(got.Codecs) != 0 {
		t.Errorf("short input = %+v, want empty", got)
	}

	// ftyp only -> SuggestedMime = "video/mp4"
	ftypOnly := makeBox("ftyp", []byte("isom\x00\x00\x00\x00isom"))
	if got := SniffMP4(ftypOnly); got.MajorBrand != "isom" || got.SuggestedMime != "video/mp4" {
		t.Errorf("ftypOnly = %+v", got)
	}

	// avc1 without avcC -> fallback codec avc1.42C020, landscape 1280x704
	stsdNoAvcC := makeBox("stsd", makeAvc1Payload(1280, 704, 0, 0, 0, false))
	gotNoAvcC := SniffMP4(stsdNoAvcC)
	if !slices.Equal(gotNoAvcC.Codecs, []string{"avc1.42C020"}) || gotNoAvcC.Width != 1280 || gotNoAvcC.Height != 704 {
		t.Errorf("stsdNoAvcC = %+v", gotNoAvcC)
	}

	// 64-bit extended size (boxSize == 1) and EOF-extending box (boxSize == 0) + hvc1/Opus/vp09 deduplication
	var extBuf bytes.Buffer
	payload := []byte("hvc1Opusvp09hvc1")
	_ = binary.Write(&extBuf, binary.BigEndian, uint32(1))
	extBuf.WriteString("trak")
	_ = binary.Write(&extBuf, binary.BigEndian, uint64(16+len(payload)))
	extBuf.Write(payload)

	// Append a box with size 0 (extends to EOF) containing mp4a
	_ = binary.Write(&extBuf, binary.BigEndian, uint32(0))
	extBuf.WriteString("mdia")
	extBuf.WriteString("mp4a")

	gotExt := SniffMP4(extBuf.Bytes())
	wantExtCodecs := []string{"hvc1.1.6.L93.B0", "opus", "vp09.00.41.08", "mp4a.40.2"}
	if !slices.Equal(gotExt.Codecs, wantExtCodecs) {
		t.Errorf("gotExt.Codecs = %v, want %v", gotExt.Codecs, wantExtCodecs)
	}
}
