# Introduction

This repository demonstrates how Gemini can be leveraged as a Snowfakery plugin for generating synthetic data based on a set of predefined schemas and data generation strategies. The framework is based on [Snowfakery](https://snowfakery.readthedocs.io/) which is itself based on [Faker](https://faker.readthedocs.io/). It requires the expected outputs to be codified in a YAML file per Snowfakery specs, detailing all the required fields and their respective data generation strategies. The framework currently supports 3 such strategies:

1. Static Values - can be included in the YAML file itself.
2. Faker based values - Leverages the Faker library to generate fake data.
3. LLM based values - Leverages an LLM (Gemini) call and a predefined prompt template to generate data

It is also possible to use arbitrary python functions to generate data and augment the pipeline. Interrelated schemas are also supported where the value of a given field depends on an already defined field, which allows us to create hierarchical data and complex schemas. The data generated via this framework is saved to a CSV file for further analysis / consumption.

While the primary purpose of the synthetic data generation pipeline is to generate data for testing, this can also be used to support tangential use-cases like running prompt experiments and comparisons at scale, building few-shot examples, evaluating fine-tuned models, etc.

# Getting started

## Codebase Setup

1. Clone the repo

   `gcloud source repos clone synthetic-data-generation -project=genai-github-assets`

2. Install Dependencies: The framework uses pyproject.toml to list dependencies, which can be installed using pip as follows:

   `pip install .`

## Codebase Walkthrough

### Recipe

In order to generate synthetic data, the schema of the synthetic data must be defined first. This is done by creating a `recipe` in a YAML format as demonstrated below, more details on writing recipes can be found [here](https://snowfakery.readthedocs.io/en/latest/#central-concepts).

#### Few central concepts to know when building a recipe

##### Objects

The core concept of Snowfakery is an object template. The object template represents instructions on how to create a row (or multiple rows) in a database. Rows, also known as records, in turn represent real-world entities such as people, places, or things, which is why we use the keyword “object”.

##### Fake Data

To generate fake data use a fake function. You can fake all sorts of data: names, addresses, Latin text, English sentences, URLs, and so much more. To see the complete list, along with other related features, see the [fake data tutorial](https://snowfakery.readthedocs.io/en/docs/fakedata.html)

##### Friends

To create a rule such as "For every Person created, create two Animals", use the friends feature. Eg:

    - object: Person
      count: 3
      fields:
        name:
          fake: name
        age:
          random_number:
            min: 12
            max: 95
      friends: # I get by with a little help from my...
        - object: Animal
          count: 2
          fields:
            name:
              fake: FirstName

### Directory Structure

    .
    ├── main.ipynb
    ├── pyproject.toml
    ├── README.md
    └── synthetic_data_generation
        ├── plugins
        │   ├── Gemini.py
        │   └── Wikipedia.py
        └── prompts
            ├── blog_generator.jinja
            └── comment_generator.jinja

`main.ipynb` - The main notebook to run the data generation pipeline. Contains the data generation recipe and the execution code.

`pyproject.toml` - Contains metadata about the project and handles dependencies.

`README.md` - Current file

`synthetic_data_generation/plugins` - Contains the custom plugins implemented to extend Snowfakery functionality. These can be directly referenced and invoked inside the recipe YAML file.

`synthetic_data_generation/plugins/Gemini.py` - The Gemini plugin provides functionality for Snowfakery to invoke LLM to generate data using a predefined prompt template. This implements a `generate` method with the following arguments:

- `prompt_name` : Denotes which prompt template is to be used.
- `temperature` : explained [here](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini#request_body)
- `top_p` : explained [here](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini#request_body)

`synthetic_data_generation/plugins/Wikipedia.py` - The wikipedia plugin provides functionality for Snowfakery to extract information for a given Wikipedia page. It implements a `get_page` method which expects a Wikipedia title as an input.

`synthetic_data_generation/prompts` - Contains custom prompt templates in the form of .jinja files.

`synthetic_data_generation/prompts/blog_generator.jinja` - The prompt used to generate blog posts.

`synthetic_data_generation/prompts/comment_generator.jinja` - The prompt used to generate comments.

## Cleaning up

Since the notebook doesn’t create any resources. To clean up all Google Cloud resources used in this project, you can [delete the Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects#shutting_down_projects) you used for the tutorial.
