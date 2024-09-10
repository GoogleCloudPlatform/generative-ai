<script lang="ts">
  import { Navbar, NavBrand, NavLi, NavUl } from "flowbite-svelte";
  import { A } from "flowbite-svelte";
  import { Heading } from "flowbite-svelte";
  import { onMount } from "svelte";

  var text = "";
  var time = 0;

  function send_input(text, time) {
    setTimeout(function () {
      document
        .querySelector("df-messenger")
        .querySelector("df-messenger-chat")
        .shadowRoot.querySelector("df-messenger-user-input")
        .shadowRoot.querySelector("textarea").value = text;
    }, time);

    setTimeout(function () {
      document
        .querySelector("df-messenger")
        .querySelector("df-messenger-chat")
        .shadowRoot.querySelector("df-messenger-user-input")
        .shadowRoot.querySelector("textarea")
        .dispatchEvent(new Event("input"));
    }, time + 100);

    setTimeout(function () {
      document
        .querySelector("df-messenger")
        .querySelector("df-messenger-chat")
        .shadowRoot.querySelector("df-messenger-user-input")
        .shadowRoot.querySelector("button")
        .click();
    }, time + 1000);
  }

  onMount(() => {
    // Write and send sample questions to chatbot
    send_input("Hello", 2000);
    send_input("Does the Pixel 7 Pro support fast charging?", 6000);
    send_input("Which colors is the Pixel Watch available in?", 11000);
  });
</script>

<Navbar let:hidden let:toggle class="bg-[#B1D6FC]">
  <NavBrand href="/">
    <img src="vertex-ai-logo.png" class="mr-3 h-6 sm:h-9" alt="Vertex AI Conversation" />
    <span class="self-center whitespace-nowrap text-xl font-semibold text-black dark:text-white"
      >Vertex AI Conversation Demo</span>
  </NavBrand>
  <NavUl {hidden}>
    <NavLi href="/" active={true}>Home</NavLi>
    <NavLi href="https://cloud.google.com/generative-ai-app-builder/docs/introduction"
      >Documentation</NavLi>
    <NavLi href="https://codelabs.developers.google.com/codelabs/vertex-ai-conversation"
      >Codelab</NavLi>
    <NavLi
      href="https://github.com/GoogleCloudPlatform/generative-ai/tree/main/conversation/chat-app"
      >Source code</NavLi>
  </NavUl>
</Navbar>

<div class="container mx-auto bg-[#E2ECF3]">
  <div class="max-h-full max-w-full bg-[#E2ECF3]">
    <div class="flex max-h-[90vh]">
      <div class="m-6 w-3/5">
        <Heading tag="h5" class="my-2">What is a Data Store Agent?</Heading>
        <p class="font-normal text-gray-700 dark:text-gray-400">
          A generative + conversational AI feature within <A
            href="https://cloud.google.com/generative-ai-app-builder"
            class="font-medium hover:underline">Vertex AI Conversation</A> and
          <A href="https://cloud.google.com/dialogflow" class="font-medium hover:underline"
            >Dialogflow CX</A
          >.
        </p>

        <Heading tag="h5" class="my-2 mt-6">How it works</Heading> You provide a website, unstructured
        data, or structured data, then Data Store Agent indexes your content and creates a virtual agent
        that is powered by large language models. Users can then chat, ask questions, and have a conversation
        about the content.

        <Heading tag="h5" class="my-2 mt-6">Try it yourself!</Heading>
        Ask the chatbot on the right about products in the Google Store, such as the Pixel Phone, Pixel
        Watch, or Pixel Tablet.

        <img
          src="how-chat-works.png"
          alt="Lifecycle of a Data Store Agent Question"
          class="mx-auto mt-4" />

        <p class="mt-6 align-bottom font-normal text-gray-700 dark:text-gray-400">
          Powered by <A
            class="font-medium hover:underline"
            href="https://cloud.google.com/generative-ai-app-builder">Vertex AI Conversation</A> and
          <A class="font-medium hover:underline" href="https://cloud.google.com/dialogflow"
            >Dialogflow CX</A>
          in <A class="font-medium hover:underline" href="https://cloud.google.com/"
            >Google Cloud</A>
        </p>
      </div>
      <div class="m-12 w-2/5">
        <script
          src="https://www.gstatic.com/dialogflow-console/fast/df-messenger/prod/v1/df-messenger.js"></script>
        <df-messenger
          project-id="your-project-id"
          agent-id="4e166055-7ed3-4ffb-abf6-ee0d75abf823"
          language-code="en"
          storage-option="none"
          class="drop-shadow-lg"
          max-query-length="-1">
          <df-messenger-chat
            chat-title="Google Store - Vertex AI Conversation"
            bot-writing-text="..."
            placeholder-text="Ask me anything about the Google Store..." />
        </df-messenger>
      </div>
    </div>
  </div>
</div>
