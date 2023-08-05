<script lang="ts">
  import { Navbar, NavBrand, NavLi, NavUl, NavHamburger } from "flowbite-svelte";
  import { Card } from "flowbite-svelte";
  import { Tabs, TabItem } from "flowbite-svelte";
</script>

<Navbar let:hidden let:toggle rounded color="form">
  <NavBrand href="/">
    <span class="self-center whitespace-nowrap text-xl font-semibold dark:text-white"
      >Google Cloud - Gen App Builder (Chat App)</span
    >
  </NavBrand>
  <NavHamburger on:click={toggle} />
  <NavUl {hidden}>
    <NavLi href="/" active={true}>Home</NavLi>
    <NavLi
      href="https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gen-app-builder/chat-app"
      >GitHub</NavLi
    >
    <NavLi href="#">Feedback</NavLi>
  </NavUl>
</Navbar>

<div id="sidebar" class="m-6">
  <script
    src="https://www.gstatic.com/dialogflow-console/fast/messenger-cx/prod/df-messenger.min.js?v=1"
  ></script>
  <df-messenger agent-id="b42e8b15-64ef-45be-bdaf-cbf78541873b" language-code="en">
    <df-messenger-chat
      chat-title="Google Store"
      bot-writing-text="..."
      placeholder-text="Ask me something..."
    />
  </df-messenger>
</div>

<Tabs
  style="full"
  defaultClass="flex rounded-lg divide-x divide-gray-200 shadow dark:divide-gray-700"
>
  <TabItem class="w-full" open>
    <span slot="title">How it works</span>
    <Card padding="none" size="full" class="grid md:grid-cols-2 m-6">
      <figure
        class="flex flex-col justify-center items-center p-8 text-center bg-white rounded-t-lg border-b border-gray-200 md:rounded-t-none md:rounded-tl-lg md:border-r dark:bg-gray-800 dark:border-gray-700"
      >
        <blockquote class="mx-auto mb-4 max-w-2xl text-gray-500 dark:text-gray-400">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Easily ingest data</h3>
          <p class="my-4 font-light">
            Including public website data, unstructured data (PDF files), structured data (JSON,
            BigQuery)
          </p>
        </blockquote>
      </figure>
      <figure
        class="flex flex-col justify-center items-center p-8 text-center bg-white rounded-tr-lg border-b border-gray-200 dark:bg-gray-800 dark:border-gray-700"
      >
        <blockquote class="mx-auto mb-4 max-w-2xl text-gray-500 dark:text-gray-400">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Generative AI answers</h3>
          <p class="my-4 font-light">
            Retrives indexed documents, then uses large language models to provide natural answers
            grounded in your data
          </p>
        </blockquote>
      </figure>
      <figure
        class="flex flex-col justify-center items-center p-8 text-center bg-white rounded-bl-lg border-b border-gray-200 md:border-b-0 md:border-r dark:bg-gray-800 dark:border-gray-700"
      >
        <blockquote class="mx-auto mb-4 max-w-2xl text-gray-500 dark:text-gray-400">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
            Multi-channel integrations
          </h3>
          <p class="my-4 font-light">
            Embed a chat widget on your website, connect to a phone gateway or telephony provider,
            or integrate with other chat and CRM tools
          </p>
        </blockquote>
      </figure>
      <figure
        class="flex flex-col justify-center items-center p-8 text-center bg-white rounded-b-lg border-gray-200 md:rounded-br-lg dark:bg-gray-800 dark:border-gray-700"
      >
        <blockquote class="mx-auto mb-4 max-w-2xl text-gray-500 dark:text-gray-400">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Try it yourself</h3>
          <p class="my-4 font-light">
            Ask the chatbot on the right questions about products in the Google Store, such as Pixel
            Phone, Pixel Watch, or Pixel Tablet
          </p>
        </blockquote>
      </figure>
    </Card>
  </TabItem>
  <TabItem class="w-full">
    <span slot="title">How we built it</span>
    <p class="text-lg">
      <b>Step 1:</b> Create a chat app and associated data store in Gen App Builder <br /><br />
      <b>Step 2:</b> Select the website data type and input your website URLs <br /><br />
      <b>Step 3:</b> Embed a chat widget into your website and delight your customers!
    </p>
  </TabItem>
</Tabs>

Powered by <a href="https://cloud.google.com/generative-ai-app-builder">Gen App Builder</a> and
<a href="https://cloud.google.com/dialogflow">Dialogflow CX</a>
in <a href="https://cloud.google.com/">Google Cloud</a>

<style>
  #sidebar {
    height: 90vh;
    width: 30vw;
    float: right;
  }
</style>
