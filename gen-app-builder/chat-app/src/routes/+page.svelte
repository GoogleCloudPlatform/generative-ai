<script lang="ts">
  import { Navbar, NavBrand, NavLi, NavUl } from "flowbite-svelte";
  import { A } from "flowbite-svelte";
  import { Heading } from "flowbite-svelte";
  import { onMount } from "svelte";

  onMount(() => {
    setTimeout(function () {
      document
        .querySelector("df-messenger")
        .querySelector("df-messenger-chat")
        .shadowRoot.querySelector("df-messenger-user-input")
        .shadowRoot.querySelector(".textarea-wrapper > textarea").value = "Hello";
    }, 1000);

    setTimeout(function () {
      document
        .querySelector("df-messenger")
        .querySelector("df-messenger-chat")
        .shadowRoot.querySelector("df-messenger-user-input")
        .shadowRoot.querySelector(".send-icon-button-wrapper > button")
        .click();
    }, 2000);

    setTimeout(function () {
      document
        .querySelector("df-messenger")
        .querySelector("df-messenger-chat")
        .shadowRoot.querySelector("df-messenger-user-input")
        .shadowRoot.querySelector(".textarea-wrapper > textarea").value =
        "Does the Pixel 7 Pro support fast charging?";
    }, 6000);

    setTimeout(function () {
      document
        .querySelector("df-messenger")
        .querySelector("df-messenger-chat")
        .shadowRoot.querySelector("df-messenger-user-input")
        .shadowRoot.querySelector(".send-icon-button-wrapper > button")
        .click();
    }, 7000);

    setTimeout(function () {
      document
        .querySelector("df-messenger")
        .querySelector("df-messenger-chat")
        .shadowRoot.querySelector("df-messenger-user-input")
        .shadowRoot.querySelector(".textarea-wrapper > textarea").value =
        "How does the Pixel Watch track sleep?";
    }, 11000);

    setTimeout(function () {
      document
        .querySelector("df-messenger")
        .querySelector("df-messenger-chat")
        .shadowRoot.querySelector("df-messenger-user-input")
        .shadowRoot.querySelector(".send-icon-button-wrapper > button")
        .click();
    }, 12000);
  });
</script>

<Navbar let:hidden let:toggle class="bg-[#B1D6FC]">
  <NavBrand href="/">
    <img src="gen-app-builder-logo.png" class="mr-3 h-6 sm:h-9" alt="Gen App Builder" />
    <span class="self-center whitespace-nowrap text-xl font-semibold text-black dark:text-white"
      >Gen App Builder - Chat App Demo</span>
  </NavBrand>
  <NavUl {hidden}>
    <NavLi href="/" active={true}>Home</NavLi>
    <NavLi href="https://cloud.google.com/generative-ai-app-builder/docs/introduction"
      >Documentation</NavLi>
    <NavLi href="https://codelabs.developers.google.com/codelabs/gen-app-builder-chat"
      >Codelab</NavLi>
    <NavLi
      href="https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gen-app-builder/chat-app"
      >Source code</NavLi>
  </NavUl>
</Navbar>

<div class="container mx-auto bg-[#E2ECF3]">
  <div class="max-h-full max-w-full bg-[#E2ECF3]">
    <div class="flex">
      <div class="m-6 w-3/5">
        <Heading tag="h5" class="my-2">What is Generative AI Agent?</Heading>
        <p class="font-normal text-gray-700 dark:text-gray-400">
          <A
            href="https://cloud.google.com/generative-ai-app-builder/docs/agent-intro"
            class="font-medium hover:underline">Generative AI Agent</A> is a feature within <A
            href="https://cloud.google.com/generative-ai-app-builder"
            class="font-medium hover:underline">Generative AI App Builder</A> that is built on top of
          <A href="https://cloud.google.com/dialogflow" class="font-medium hover:underline"
            >Dialogflow CX</A
          >.
        </p>

        <Heading tag="h5" class="my-2 mt-6">Try it yourself!</Heading>
        Ask the chatbot on the right about products in the Google Store, such as the Pixel Phone, Pixel
        Watch, or Pixel Tablet

        <Heading tag="h5" class="my-2 mt-6">How it works</Heading>
        You provide a website or structured/unstructured data, then Generative AI Agent parses your content
        and creates a virtual agent that is powered by large language models. Users can then chat and
        ask questions about the content.

        <img
          src="how-chat-works.png"
          alt="Lifecycle of a Generative AI Agent Question"
          class="mx-auto mt-4" />

        <p class="mt-6 align-bottom font-normal text-gray-700 dark:text-gray-400">
          Powered by <A
            class="font-medium hover:underline"
            href="https://cloud.google.com/generative-ai-app-builder">Gen App Builder</A> and
          <A class="font-medium hover:underline" href="https://cloud.google.com/dialogflow"
            >Dialogflow CX</A>
          in <A class="font-medium hover:underline" href="https://cloud.google.com/"
            >Google Cloud</A>
        </p>
      </div>
      <div class="m-12 w-2/5">
        <script
          src="https://www.gstatic.com/dialogflow-console/fast/messenger-cx/prod/df-messenger.min.js?v=1"></script>
        <df-messenger
          agent-id="b42e8b15-64ef-45be-bdaf-cbf78541873b"
          language-code="en"
          storage-option="none"
          class="drop-shadow-lg">
          <df-messenger-chat
            chat-title="Google Store - Generative AI Agent"
            bot-writing-text="..."
            placeholder-text="Ask me anything about the Google Store..." />
        </df-messenger>
      </div>
    </div>
  </div>
</div>
