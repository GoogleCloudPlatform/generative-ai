type Image = {
  gcsUri?: string;
  imageBytes?: ArrayBuffer;
  encodedImage?: string;
  mimeType?: string;
};

export type GeneratedImage = {
  image?: Image;
  raiFilteredReason?: string;
  enhancedPrompt?: string;
};
