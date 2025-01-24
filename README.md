 # ArXiv Paper Summarizer

## Table of Contents

- [Features](#features)
- [Setup](#setup)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Running with GitHub Actions](#running-with-github-actions)
  - [Running Locally](#running-locally)
  - [Configuration Details](#configuration-details)
- [How It Works](#how-it-works)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

This project is a daily ArXiv paper scanner that uses a large language model (LLM) and author matching to identify relevant papers. It can be configured to run daily via GitHub Actions, posting updates to Slack and/or rendering a static website with the results.

## Features

- **Multi-Source Support**: Currently supports arXiv with plans to integrate HuggingFace Daily Papers
- **Advanced Filtering**: Uses abstract-based filtering for more accurate paper selection
- **Custom LLM Connections**: Leverages LiteLLM for seamless integration with hundreds of different LLMs
- **Fast AI QA**: Implements caching using Google Gemini for efficient question-answering
- **Topic Classification**: Organizes papers by topics with web-based sorting capabilities
- **Enhanced UI**: Features a more aesthetically pleasing and user-friendly web interface
- **Modular Codebase**: Refactored for easy customization and extension
- **History Tracking**: Convenient page for saving and retrieving paper history
- **Docker Support**: Easy deployment using Docker containers

- **Daily ArXiv Scanning**: Automatically fetches new papers from ArXiv based on specified categories.
- **Intelligent Filtering**: Uses a combination of author matching and LLM-based relevance scoring to filter papers.
- **Customizable Prompts**: Allows users to define specific criteria for paper selection using a prompt.
- **Multiple Output Options**: Supports output to Slack, static markdown files, and a web interface.
- **Q&A Generation**: Generates question-answer pairs for each paper using an LLM.
- **Caching**: Implements caching to avoid redundant processing and reduce API costs.
- **Web Interface**: Provides a Flask-based web interface to view the daily paper summaries and Q&A.

## Setup

### Prerequisites

- Python 3.7+
- A GitHub repository
- An OpenAI API key or a Gemini API key
- (Optional) A Semantic Scholar API key
- (Optional) A Slack API key and channel ID

### Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/your-username/your-repo.git
    cd your-repo
    ```

2. Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

### Configuration

1. **API Keys**:
    - Set your OpenAI API key or Gemini API key as `GEMINI_API_KEY` in `configs/keys.ini`.
    - (Optional) Set your Semantic Scholar API key as `S2_API_KEY` in `configs/keys.ini`.
    - (Optional) Set your Slack API key as `SLACK_KEY` and channel ID as `SLACK_CHANNEL_ID` in your environment variables or GitHub secrets.
        - To set environment variables, you can use the `export` command in your terminal (e.g. `export SLACK_KEY=your_slack_key`).
        - To set GitHub secrets, go to your repository settings, then "Secrets and variables", then "Actions".
2. **Paper Topics**:
    - Create a `configs/paper_topics.txt` file and fill it with the types of papers you want to follow. See the example in the file for formatting.
3. **Authors**:
    - Create a `configs/authors.txt` file and list the authors you want to follow, along with their Semantic Scholar IDs.
4. **ArXiv Categories**:
    - Set your desired ArXiv categories in `configs/config.ini`.
5. **Output Options**:
    - Configure output options (JSON, Markdown, Slack) in `configs/config.ini`.

### Running with GitHub Actions

1. Fork this repository to your GitHub account.
2. Enable scheduled workflows in your repository settings.
3. Add your API keys as GitHub secrets.
4. Set GitHub Pages build source to GitHub Actions.
5. The bot will run daily at 1 PM UTC, posting to Slack (if configured) and publishing a GitHub Pages website.

### Running Locally

### Docker Usage

#### Build the Docker Image

```bash
docker build -t arxiv-paper-summarizer .
```

#### Run the Docker Container

```bash
docker run -d -p 8000:8000 \
  -v /path/to/your/configs:/app/configs \
  -e GEMINI_API_KEY=your_api_key \
  arxiv-paper-summarizer
```

#### Environment Variables

- `GEMINI_API_KEY`: Your Google Gemini API key (required)
- `SLACK_KEY`: Slack API key (optional)
- `SLACK_CHANNEL_ID`: Slack channel ID (optional)

#### Persistent Storage

- Mount your config directory to `/app/configs` to persist configuration files
- Mount a data directory to `/app/data` to persist paper history and cache

#### Docker Compose Example

```yaml
version: '3'
services:
  arxiv-summarizer:
    image: arxiv-paper-summarizer
    ports:
      - "8000:8000"
    volumes:
      - ./configs:/app/configs
      - ./data:/app/data
    environment:
      environment:
        - GEMINI_API_KEY=${GEMINI_API_KEY}
    restart: unless-stopped
```

1. Build the Docker image:

    ```bash
    docker build -t arxiv-paper-summarizer .
    ```

2. Run the Docker container:

    ```bash
    docker run -d -p 8000:8000 -v /path/to/your/configs:/app/configs arxiv-paper-summarizer
    ```

    The application will be available at <http://localhost:8000>.

### Running Locally

1. Set up the environment using `requirements.txt`:

    ```bash
    pip install -r requirements.txt
    ```

2. Set environment variables for `GEMINI_API_KEY`, `SLACK_KEY`, and `SLACK_CHANNEL_ID` (if using Slack).

3. Run the CLI tool:

    ```bash
    # Generate paper summaries
    paper-assistant generate [options]
    
    # Options:
    #   --output-format markdown,json,slack  # Specify output formats
    #   --config path/to/config.ini          # Custom config file
    #   --authors path/to/authors.txt        # Custom authors file
    #   --debug                              # Enable debug messages
    #   --query "your arxiv query"           # Custom ArXiv query

    # Start the web server
    paper-assistant serve [options]
    
    # Options:
    #   --port 8000                          # Custom port (default: 5000)
    #   --debug                              # Enable debug mode

    # Get help
    paper-assistant --help
    ```

    Example commands:

    ```bash
    # Generate papers with all output formats
    paper-assistant generate --output-format markdown,json,slack --debug

    # Use custom configuration
    paper-assistant generate --config custom_config.ini --authors custom_authors.txt

    # Start web server on port 8000
    paper-assistant serve --port 8000 --debug
    ```

### Configuration Details

- `configs/config.ini`: Contains settings for filtering, output, and model selection.
- `configs/paper_topics.txt`: Defines the criteria for paper selection.
- `configs/authors.txt`: Lists authors to follow, along with their Semantic Scholar IDs.
- `configs/questions.txt`: Contains the questions used for Q&A generation. These questions are used by the LLM to generate question-answer pairs for each paper.

## How It Works

1. **ArXiv Fetching**: The script fetches new papers from ArXiv RSS feeds based on the specified categories.
2. **Author Matching**: It checks if any of the paper's authors match the authors listed in `configs/authors.txt`.
3. **LLM Filtering**:
    - Papers are filtered based on the h-index of their authors.
    - The remaining papers are evaluated by an LLM using the prompt in `configs/paper_topics.txt`.
    - The LLM scores papers for relevance and novelty.
4. **Q&A Generation**: For each selected paper, the script downloads the PDF and generates question-answer pairs using an LLM, based on the questions in `configs/questions.txt`.
5. **Output**: The selected papers are sorted by their combined scores and output to the specified endpoints (Slack, JSON, Markdown, or web interface).

## Contributing [TODO]

- This project uses `ruff` for linting and formatting.
- Install the pre-commit hook by running `pre-commit install`.
- Run `ruff check .` and `ruff format .` to check and format your code.

## License

This project is licensed under the Apache 2.0 License. See the `LICENSE` file for details.

## Acknowledgements

This project was originally built by Tatsunori Hashimoto and is licensed under the Apache 2.0 license. Thanks to Chenglei Si for testing and benchmarking the LLM filter.
