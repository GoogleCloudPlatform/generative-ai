<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <v-sheet class="pa-2 mt-6" rounded="lg" color="red" fluid>
          <v-row>
            <v-col class="d-flex flex-column align-center">
              <v-img class="mt-n10" :width="60" src="../assets/logo.png" elevated></v-img>
              <h2>cherrypicker.ai</h2>
            </v-col>
          </v-row>
        </v-sheet>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <v-sheet class="pa-6 text-center" rounded="lg">
          <div v-if="preview">
            <v-img v-if="!isEditedImg" rounded="lg" max-height="25vh" :src="preview"></v-img>
            <v-img v-if="isEditedImg" rounded="lg" max-height="25vh" :src="editedPreview"></v-img>
            <p v-if="isEditedImg" class="pt-1 text-caption text-grey font-italic">edited image</p>
          </div>
          <div v-if="!preview" class="text-center">
            <v-img rounded="lg" max-height="20vh" src="../assets/cherry.png"></v-img>
            <p class="pt-6 text-body-2">{{ instruction }}</p>
          </div>
          <v-file-input class="pt-6" ref="imgInput" label="Upload image of your produce" hide-details prepend-icon=""
            variant="outlined" chips @change="previewImage" @click:clear="reset" accept=".png, .jpg, .jpeg">
            <template v-slot:append>
              <v-icon @click="$refs.imgInput.click()">mdi-camera</v-icon>
            </template>
          </v-file-input>
        </v-sheet>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-sheet v-if="preview" rounded="lg" class="pa-6 overflow-y-auto relative" max-height="50vh">
          <v-progress-linear v-if="isLoading" class="mt-6" color="red" indeterminate></v-progress-linear>
          <p v-if="isLoading" class="pt-6 text-body-2">{{ loadingText }}</p>
          <p v-if="!isLoading && showSingleProduceRating" class="text-h5 text-capitalize">
            {{ produceName }} Rating</p>
          <p v-if="!isLoading && showBulkProduceSelector" class="text-h5 text-capitalize">
            Best {{ produceName }}</p>
          <p v-if="!isLoading && showBulkProduceSelector">{{ bulkProduceSelector }}</p>
          <br v-if="!isLoading && showSingleProduceRating">
          <div v-if="!isLoading && showNoProduce">
            <v-chip color="red" variant="flat">
              No produce found in this image!
            </v-chip>
          </div>
          <div v-if="!isLoading && showSingleProduceRating" class="d-flex align-center">
            <b>Overall Rating: </b><v-rating readonly half-increments :length="5" :size="24"
              :model-value="singleProduceRating['Overall Rating']" color="yellow-darken-3" />
          </div>
          <div v-if="!isLoading && showSingleProduceRating && showMarketing" class="py-3">
            <v-fab v-if="showMarketing" @click="marketingDialog = true" extended prepend-icon="mdi-cart"
              text="Find Fresher Produce" color="green"></v-fab>
          </div>
          <div v-if="!isLoading && showSingleProduceRating">
            <br>
            <b>Reasoning for Rating:</b> {{ singleProduceRating['Reasoning for Rating'] }}
          </div>
          <div v-if="!isLoading && showSingleProduceRating">
            <br>
            <b>Pros of Produce Selected:</b>
            <ul class="ml-3">
              <li v-for="(pro, index) in singleProduceRating['Pros of Produce Selected']" :key="index">
                {{ pro }}
              </li>
            </ul>
          </div>
          <div v-if="!isLoading && showSingleProduceRating">
            <br>
            <b>Cons of Produce Selected:</b>
            <ul class="ml-3">
              <li v-for="(con, index) in singleProduceRating['Cons of Produce Selected']" :key="index">
                {{ con }}
              </li>
            </ul>
          </div>

          <v-dialog v-if="showMarketing" v-model="marketingDialog">
            <v-card>
              <div v-if="!isMarketingLoading" class="pa-6" v-html="marketingData"></div>
              <div v-if="isMarketingLoading" class="pa-6">
                <v-progress-linear class="mt-6" color="red" indeterminate></v-progress-linear>
                <p class="pt-6 text-body-2">{{ loadingText }}</p>
              </div>
              <v-card-actions v-if="!isMarketingLoading">
                <v-spacer></v-spacer>

                <v-btn text="Close" variant="text" @click="marketingDialog = false"></v-btn>

                <v-btn color="green" text="View Weekly Flyers" variant="elevated" @click="openRandomUrl"></v-btn>
              </v-card-actions>
            </v-card>
          </v-dialog>
        </v-sheet>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import MarkdownIt from 'markdown-it';
export default {
  data: () => ({
    preview: null,
    editedPreview: null,
    image: [],
    res: null,
    instructions: [
      'Please upload an image of your produce.',
      'Ensure the image is clear and well-lit.',
      'Gemini will analyze the image and provide insights.'
    ],
    currentInstructionIndex: 0,
    marketingData: 'marketing data goes here',
    instruction: 'Please upload an image of your produce.',
    singleProduceRating: `{single_produce_rating: "{"Absence of Defects Rating": 1, "Cons of Produce Selected": {"First Con": "Avoid apples with shriveled skin, bruises, or discoloration.", "Second Con": "Check for firmness; a good apple should be firm to the touch, not soft or mushy.", "Third Con": "Inspect for any signs of mold, decay, or insect damage."}, "Freshness Rating": 1, "Overall Rating": 1, "Pros of Produce Selected": {"First Pro": "This apple would make excellent 'compost-starter'.", "Second Pro": "The overripe apple can be a 'sweet treat' for certain wildlife or insects."}, "Quality Rating": 1, "Reasoning for Rating": "This apple exhibits significant decay and shriveling, indicating it is well past its prime. The large brown, mushy area signifies spoilage, making it unsuitable for consumption.  The skin shows dehydration and likely an advanced stage of rot. Due to these factors, it receives a low rating across all categories."}"}`,
    bulkProduceSelector: 'bulk produce selector response goes here...',
    loadingTexts: [
      'Sprinkling some Gemini magic on your image...',
      'Consulting the oracles of produce...',
      'Unveiling the secrets of your delicious image...',
      'Gemini is hard at work, crunching pixels...',
      'Hold tight, the results are almost ripe...'
    ],
    currentLoadingIndex: 0,
    loadingText: 'Sprinkling some Gemini magic on your image...',
    isLoading: false,
    isEditedImg: false,
    showMarketing: false,
    showSingleProduceRating: false,
    showBulkProduceSelector: false,
    marketingDialog: false,
    produceName: 'produce name here',
    isMarketingLoading: false,
    showNoProduce: false,
    urls: [
      "https://drive.google.com/file/d/1HEVIiLMVZ7V5V8XiWTo88-22WNfUdMji/view?usp=drive_link",
      // "https://drive.google.com/file/d/1XXTWFqpalAZjRCqDbNwp4q7JNeGcJqid/view?usp=drive_link",
      // "https://drive.google.com/file/d/1dplRr-7VVtbCQb4MTQSO-hT8tjJ5IQWx/view?usp=drive_link",
    ],
  }),
  mounted() {
    this.interval = setInterval(() => {
      this.currentInstructionIndex = (this.currentInstructionIndex + 1) % this.instructions.length;
      this.instruction = this.instructions[this.currentInstructionIndex];
      this.currentLoadingIndex = (this.currentLoadingIndex + 1) % this.loadingTexts.length;
      this.loadingText = this.loadingTexts[this.currentLoadingIndex];
    }, 3000);
  },
  methods: {
    previewImage(event) {
      var input = event.target;
      if (input.files) {
        var reader = new FileReader();
        reader.onload = (e) => {
          this.preview = e.target.result
        }
        reader.readAsDataURL(input.files[0]);
        this.sendImage(input.files[0]);
        this.isLoading = true;
      }
    },
    reset() {
      this.image = null;
      this.preview = null;
      this.isEditedImg = false;
      this.showMarketing = false;
      this.showSingleProduceRating = false;
      this.showBulkProduceSelector = false;
      this.isLoading = false;
      this.isMarketingLoading = false;
      this.showNoProduce = false;
    },
    async sendImage(imgFile) {
      const formData = new FormData();
      formData.append('file', imgFile);

      try {
        var response = await fetch('/api/start_receiver', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          var errorData = await response.json();
          throw new Error(`HTTP error ${response.status}: ${errorData.message || response.statusText}`);
        }

        this.res = await response.json();
        if (this.res['no_produce']) {
          this.showNoProduce = true;
          this.isLoading = false;
        }
        if (this.res['single_produce_rating']) {
          this.singleProduceRating = JSON.parse(this.res['single_produce_rating']);
          this.showSingleProduceRating = true;
          this.produceName = this.res['produce_name'];
          if (this.singleProduceRating['Overall Rating'] <= 2.5) {
            this.isMarketingLoading = true;
            this.requestMarketing(this.produceName, this.singleProduceRating);
            this.showMarketing = true;
          }
          this.isLoading = false;
        } else if (this.res['bulk_produce_selector']) {
          this.isEditedImg = true;
          this.bulkProduceSelector = this.res['bulk_produce_selector'];
          this.produceName = this.res['produce_name'];
          this.editedPreview = 'data:image/png;base64,' + this.res['image'];
          this.showBulkProduceSelector = true;
          this.isLoading = false;
        }
      } catch (error) {
        console.error('Error fetching data:', error);
        this.res = { error: error.message };
      }
    },
    async requestMarketing(produceName, produceReview) {
      const formData = new FormData();
      formData.append('produce_name', { 'produce_name': produceName });
      formData.append('produce_review', JSON.stringify({ 'rating': produceReview['Overall Rating'], 'quality_reasoning': produceReview['Reasoning for Rating'], 'pros': produceReview['Pros of Produce Selected'], 'cons': produceReview['Cons of Produce Selected'] }));
      try {
        var response = await fetch('/api/request_marketing', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          var errorData = await response.json();
          throw new Error(`HTTP error ${response.status}: ${errorData.message || response.statusText}`);
        }

        this.res = await response.json();
        if (this.res['marketing']) {
          this.marketingData = this.res['marketing'];
          var md = new MarkdownIt();
          this.marketingData = md.render(this.res['marketing']);
          this.isMarketingLoading = false;
        }
      } catch (error) {
        console.error('Error fetching data:', error);
        this.res = { error: error.message };
      }
    },
    openRandomUrl() {
      const randomIndex = Math.floor(Math.random() * this.urls.length);
      const url = this.urls[randomIndex];
      window.open(url, "_blank");
    }
  }
}
</script>