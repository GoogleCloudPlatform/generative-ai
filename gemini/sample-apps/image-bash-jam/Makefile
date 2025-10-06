
# auth:
# 	gcloud config set account ricc@google.com
# 	gcloud auth login
# 	gcloud auth application-default login
# 	gcloud config set project ricc-genai
# 	gcloud auth application-default set-quota-project ricc-genai

setup:
	./01-setup.sh

age-test:
	GENERATE_MP3=true ./gemini-generic.sh images/ricc-family-with-santa.jpg Tell me the age of the 5 people you see, from left to right.

annotate:
	./annotate-all.sh

explain-cat:
	./gemini-explain-image.sh images/cat.jpg

compare-two-ricc-pics:
	./gemini-generic-two-pics.sh images/riccardo-jogging-by-lake-ugly.jpg images/ricc-presenting-slides-vienna.jpg

compare-two-geminis:
	./gemini-generic-two-pics.sh  images/gemini-constellation.png   images/saga-blue-hair.jpg

read-instruction-manual-for-me:
#	echo 1. Explaining what this is:#
#	./gemini-explain-image.sh images/instruction-manuals/Acrux-User-Manual-4700503.png
	echo '1. Asking a useful custom question: '
	./gemini-generic.sh images/instruction-manuals/Acrux-User-Manual-4700503.png '1. How do i TURN it on? 2. Where is the power button located? 3. Is this the one called ANC?'

compare-ale-seby:
	./gemini-generic-two-pics.sh images/ale*.jpg
clean:
	rm t .tmp* t.audio* t.*.mp3 t.mp3 images-download/ images/ .tmp.*.json t
clean-all:
	rm images/*.mp3 images/*.explain.txt
	make clean

vertexai-images/sky.jpg:
	gsutil ls "gs://cloud-samples-data/generative-ai/image/"
	gsutil -m cp -r gs://cloud-samples-data/generative-ai/image/* ./vertexai-images/

# Test without Carlessian scripts
test-ricc-mac:
	PATH=/bin/:/usr/bin/:/opt/homebrew/bin/:"/Users/ricc/Library/Application Support/cloud-code/installer/google-cloud-sdk/bin/" make age-test

.PHONY: images
images:
#	echo "target is $@"
	mkdir -p "$@"
	gsutil -m rsync -r gs://github-repo/use-cases/image-bash-jam/ $@/
# moves images to above dir:
	mv $@/img/* $@/

# images-upload:
# 	gsutil rsync -r images gs://github-repo/use-cases/image-bash-jam/
