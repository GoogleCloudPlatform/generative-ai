# Generative AI - Gemini

Welcome to the Google Cloud [Generative AI](https://cloud.google.com/ai/generative-ai/) - Gemini folder.

## Gemini

<!-- markdownlint-disable MD033 -->
<img src="https://lh3.googleusercontent.com/eDr6pYKs1tT0iK0nt3pPhvVlP2Wn96fbGqbWgBAARRZ7isej037g_tWobjV8zQkxOsWzJuEH8p-fksczXUOeqxGZZIo_HUCdkn8q-a4fuwATD7Q9Xrs=w2456-l100-sg-rj-c0xffffff" style="width:35em" alt="Welcome to the Gemini era">
<!-- markdownlint-enable MD033 -->

Gemini is a family of generative AI models developed by Google DeepMind that is designed for multimodal use cases. The Gemini API gives you access to the Gemini Pro Vision and Gemini Pro models.

### Gemini API in Vertex AI

On Google Cloud, the Gemini API in Vertex AI provides a unified interface for interacting with Gemini models. There are currently two models available in the Gemini API:

- **Gemini Pro model** (`gemini-pro`): Designed to handle natural language tasks, multi-turn text and code chat, and code generation.
- **Gemini Pro Vision model** (`gemini-pro-vision`): Supports multimodal prompts. You can include text, images, and video in your prompt requests and get text or code responses.

The notebooks and samples in this folder focus on using the **Vertex AI SDK for Python** to call the Gemini API in Vertex AI.

## Using this repository

<!-- markdownlint-disable MD033 -->
<table>
  <tr>
    <th></th>
    <th style="text-align: center;">Description</th>
  </tr>
  <tr>
    <td>
      <img src="https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/flag/default/40px.svg" alt="flag">
      <br>
      <a href="getting-started/"><code>getting-started/</code></a>
    </td>
    <td>Get started with the Gemini API in Vertex AI:
      <ul>
        <li><code>gemini-1.5-pro</code> model</li>
        <li><code>gemini-1.5-flash</code> model</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td>
      <img src="https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/deployed_code/default/40px.svg" alt="deployed_code">
      <br>
      <a href="sample-apps/"><code>sample-apps/</code></a>
    </td>
    <td>Discover sample apps using Gemini</td>
  </tr>
  <tr>
    <td>
      <img src="https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/manufacturing/default/40px.svg" alt="manufacturing">
      <br>
      <a href="use-cases/"><code>use-cases/</code></a>
    </td>
    <td>Explore industry use-cases enabled by Gemini (e.g. retail, education)</td>
  </tr>
  <tr>
    <td>
      <img src="https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/radar/default/40px.svg" alt="radar">
      <br>
      <a href="evaluation/"><code>evaluation/</code></a>
    </td>
    <td>Learn how to evaluate Gemini with Vertex AI Model Evaluation for Generative AI</td>
  </tr>
  <tr>
    <td>
      <img src="https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/terminal/default/40px.svg" alt="terminal">
      <br>
      <a href="function-calling/"><code>function-calling/</code></a>
    </td>
    <td>Learn how to use the <a href="https://cloud.google.com/vertex-ai/docs/generative-ai/multimodal/function-calling">function calling</a> feature of Gemini</td>
  </tr>
  <tr>
    <td>
      <img src="https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/grass/default/40px.svg" alt="grass">
      <br>
      <a href="grounding/"><code>grounding/</code></a>
    </td>
    <td>Learn how to use the <a href="https://cloud.google.com/vertex-ai/generative-ai/docs/grounding/overview">grounding</a> feature of Gemini</td>
  </tr>
  <tr>
    <td>
      <img src="https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/neurology/default/40px.svg" alt="neurology">
      <br>
      <a href="knowledge-engine/"><code>knowledge-engine/</code></a>
    </td>
    <td>Discover how to utilize the <a href="https://cloud.google.com/vertex-ai/generative-ai/docs/rag-overview">Knowledge Engine</a> feature of Vertex AI</td>
  </tr>
  <tr>
    <td>
      <img src="https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/media_link/default/40px.svg" alt="media_link">
      <br>
      <a href="prompts/"><code>prompts/</code></a>
    </td>
    <td>Learn how to create and use effective prompts with Gemini.</td>
  </tr>
  <tr>
    <td>
      <img src="https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/question_answer/default/40px.svg" alt="question_answer">
      <br>
      <a href="qa-ops/"><code>qa-ops/</code></a>
    </td>
    <td>Learn about the question-answer operations available in Gemini</td>
  </tr>
  <tr>
    <td>
      <img src="https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/build/default/40px.svg" alt="build">
      <br>
      <a href="reasoning-engine/"><code>reasoning-engine/</code></a>
    </td>
    <td>Discover how to utilize the <a href="https://cloud.google.com/vertex-ai/generative-ai/docs/reasoning-engine/overview">Reasoning Engine</a> feature of Vertex AI</td>
  </tr>
  <tr>
    <td>
      <img src="https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/health_and_safety/default/40px.svg" alt="health_and_safety">
      <br>
      <a href="responsible-ai/"><code>responsible-ai/</code></a>
    </td>
    <td>Learn best practices for responsible AI and security with the Gemini API in Vertex AI.</td>
  </tr>
  <tr>
    <td>
      <img src="https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/tune/default/40px.svg" alt="tune">
      <br>
      <a href="tuning/"><code>tuning/</code></a>
    </td>
    <td>Learn how to tune and customize the Gemini models for specific use-cases.</td>
  </tr>
</table>
<!-- markdownlint-enable MD033 -->

## Contributing

Contributions welcome! See the [Contributing Guide](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/CONTRIBUTING.md).

## Getting help

Please use the [issues page](https://github.com/GoogleCloudPlatform/generative-ai/issues) to provide suggestions, feedback or submit a bug report.

## Disclaimer

This repository itself is not an officially supported Google product. The code in this repository is for demonstrative purposes only.
