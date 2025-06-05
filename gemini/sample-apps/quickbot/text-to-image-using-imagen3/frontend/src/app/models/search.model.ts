/**
 * Copyright 2025 Google LLC
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

export type SearchRequest = {
  term: string;
  generationModel: string;
  aspectRatio: string;
  imageStyle: string;
  numberOfImages: number;
};

export type SearchResponse = {
  summary: any;
  results: SearchResult[];
  totalSize: number;
};

export type SearchResult = {
  document: Document;
};

export type Document = {
  derivedStructData: DocumentData;
};

export type DocumentData = {
  title: string;
  link: string;
  snippets: Snippet[];
  pagemap: PageMap;
};

export type Snippet = {
  snippet: string;
};

export type PageMap = {
  cse_image: ImagesData[];
};

export type ImagesData = {
  src: string;
};
