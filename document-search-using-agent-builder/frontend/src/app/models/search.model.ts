export type SearchRequest = {
  term: string
}

export type SearchResponse = {
  summary: any
  results: SearchResult[]
  totalSize: number
}

export type SearchResult = {
  document: Document
}

export type Document = {
  derivedStructData: DocumentData
}

export type DocumentData = {
  title: string
  link: string
  snippets: Snippet[]
  pagemap: PageMap
}

export type Snippet = {
  snippet: string
}

export type PageMap = {
  cse_image: ImagesData[]
}

export type ImagesData = {
  src: string
}
