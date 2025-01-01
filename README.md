# ArXiv Paper Summarizer

This project is a daily ArXiv paper scanner that uses a large language model (LLM) and author matching to identify relevant papers. It can be configured to run daily via GitHub Actions, posting updates to Slack and/or rendering a static website with the results.

A live demo of the daily papers can be seen [here](https://tatsu-lab.github.io/gpt_paper_assistant/) running on `cs.CL`.

## Features

-   **Daily ArXiv Scanning**: Automatically fetches new papers from ArXiv based on specified categories.
-   **Intelligent Filtering**: Uses a combination of author matching and LLM-based relevance scoring to filter papers.
-   **Customizable Prompts**: Allows users to define specific criteria for paper selection using a prompt.
-   **Multiple Output Options**: Supports output to Slack, static markdown files, and a web interface.
-   **Q&A Generation**: Generates question-answer pairs for each paper using an LLM.
-   **Caching**: Implements caching to avoid redundant processing and reduce API costs.
-   **Web Interface**: Provides a Flask-based web interface to view the daily paper summaries and Q&A.

## Setup

### Prerequisites

-   Python 3.7+
-   A GitHub repository
-   An OpenAI API key or a Gemini API key
-   (Optional) A Semantic Scholar API key
-   (Optional) A Slack API key and channel ID

### Installation

1.  Clone the repository:

    ```bash
    git clone https://github.com/your-username/your-repo.git
    cd your-repo
    ```
2.  Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

### Configuration

1.  **API Keys**:
    -   Set your OpenAI API key or Gemini API key as `GEMINI_API_KEY` in `configs/keys.ini`.
    -   (Optional) Set your Semantic Scholar API key as `S2_API_KEY` in `configs/keys.ini`.
    -   (Optional) Set your Slack API key as `SLACK_KEY` and channel ID as `SLACK_CHANNEL_ID` in your environment variables or GitHub secrets.
2.  **Paper Topics**:
    -   Create a `configs/paper_topics.txt` file and fill it with the types of papers you want to follow. See the example in the file for formatting.
3.  **Authors**:
    -   Create a `configs/authors.txt` file and list the authors you want to follow, along with their Semantic Scholar IDs.
4.  **ArXiv Categories**:
    -   Set your desired ArXiv categories in `configs/config.ini`.
5.  **Output Options**:
    -   Configure output options (JSON, Markdown, Slack) in `configs/config.ini`.

### Running with GitHub Actions

1.  Fork this repository to your GitHub account.
2.  Enable scheduled workflows in your repository settings.
3.  Add your API keys as GitHub secrets.
4.  Set GitHub Pages build source to GitHub Actions.
5.  The bot will run daily at 1 PM UTC, posting to Slack (if configured) and publishing a GitHub Pages website.

### Running Locally

1.  Set up the environment using `requirements.txt`.
2.  Set environment variables for `GEMINI_API_KEY`, `SLACK_KEY`, and `SLACK_CHANNEL_ID` (if using Slack).
3.  Run the main script:

    ```bash
    python main.py
    ```

### Configuration Details

-   `configs/config.ini`: Contains settings for filtering, output, and model selection.
-   `configs/paper_topics.txt`: Defines the criteria for paper selection.
-   `configs/authors.txt`: Lists authors to follow, along with their Semantic Scholar IDs.
-   `configs/questions.txt`: Contains the questions used for Q&A generation.

## How It Works

1.  **ArXiv Fetching**: The script fetches new papers from ArXiv RSS feeds based on the specified categories.
2.  **Author Matching**: It checks if any of the paper's authors match the authors listed in `configs/authors.txt`.
3.  **LLM Filtering**:
    -   Papers are filtered based on the h-index of their authors.
    -   The remaining papers are evaluated by an LLM using the prompt in `configs/paper_topics.txt`.
    -   The LLM scores papers for relevance and novelty.
4.  **Q&A Generation**: For each selected paper, the script downloads the PDF and generates question-answer pairs using an LLM, based on the questions in `configs/questions.txt`.
5.  **Output**: The selected papers are sorted by their combined scores and output to the specified endpoints (Slack, JSON, Markdown, or web interface).

## Contributing

-   This project uses `ruff` for linting and formatting.
-   Install the pre-commit hook by running `pre-commit install`.
-   Run `ruff check .` and `ruff format .` to check and format your code.

### Testing and Improving the LLM Filter

-   The `filter_papers.py` script can be run standalone to test the LLM filter.
-   It takes a batch of papers from `in/debug_papers.json`, runs the filter, and outputs the results to `out/filter_paper_test.debug.json`.
-   Use `out/gpt_paper_batches.debug.json` to debug the LLM's output.

## License

This project is licensed under the Apache 2.0 License. See the `LICENSE` file for details.

## Acknowledgements

This project was originally built by Tatsunori Hashimoto and is licensed under the Apache 2.0 license. Thanks to Chenglei Si for testing and benchmarking the LLM filter.
