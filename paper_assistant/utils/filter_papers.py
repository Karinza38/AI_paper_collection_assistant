import configparser
import dataclasses
import json
from typing import List

from tqdm import tqdm
import instructor
from litellm import completion
from pydantic import BaseModel, Field

from paper_assistant.core.arxiv_scraper import Paper
from paper_assistant.core.arxiv_scraper import EnhancedJSONEncoder
import os

from paper_assistant.utils.helpers import argsort


class PaperScore(BaseModel):
    """Model for paper scoring response from LLM"""

    ARXIVID: str = Field(description="The arxiv ID of the paper")
    RELEVANCE: int = Field(description="Relevance score from 1-10")
    NOVELTY: int = Field(description="Novelty score from 1-10")
    COMMENT: str = Field(description="Brief comment about the paper")
    CRITERION: str = Field(description="Which criterion this paper matches")


class FilteredPapers(BaseModel):
    """Model for filtered paper IDs"""

    filtered_ids: List[str] = Field(description="List of arxiv IDs to filter out")


def filter_by_author(all_authors, papers, author_targets, config):
    # filter and parse the papers
    selected_papers = {}  # pass to output
    all_papers = {}  # dict for later filtering
    sort_dict = {}  # dict storing key and score

    # author based selection
    for paper in papers:
        all_papers[paper.arxiv_id] = paper
        for author in paper.authors:
            if author in all_authors:
                for alias in all_authors[author]:
                    if alias["authorId"] in author_targets:
                        selected_papers[paper.arxiv_id] = {
                            **dataclasses.asdict(paper),
                            **{"COMMENT": "Author match"},
                        }
                        sort_dict[paper.arxiv_id] = float(
                            config["SELECTION"]["author_match_score"]
                        )
                        break
    return selected_papers, all_papers, sort_dict


def filter_papers_by_hindex(all_authors, papers, config):
    # filters papers by checking to see if there's at least one author with > hcutoff hindex
    paper_list = []
    for paper in papers:
        max_h = 0
        for author in paper.authors:
            if author in all_authors:
                max_h = max(
                    max_h, max([alias["hIndex"] for alias in all_authors[author]])
                )
        if max_h >= float(config["FILTERING"]["hcutoff"]):
            paper_list.append(paper)
    return paper_list


def calc_price(model, usage):
    if model == "gpt-4-1106-preview":
        return (0.01 * usage.prompt_tokens + 0.03 * usage.completion_tokens) / 1000.0
    if model == "gpt-4":
        return (0.03 * usage.prompt_tokens + 0.06 * usage.completion_tokens) / 1000.0
    if (model == "gpt-3.5-turbo") or (model == "gpt-3.5-turbo-1106"):
        return (0.0015 * usage.prompt_tokens + 0.002 * usage.completion_tokens) / 1000.0
    if "gemini" in model:
        return 0


def run_and_parse_chatgpt(full_prompt, client, config):
    try:
        response = client.chat.completions.create(
            model=config["SELECTION"]["model"],
            messages=[{"role": "user", "content": full_prompt}],
            max_tokens=4096,
            response_model=List[PaperScore],
            temperature=0.0,
            max_retries=3,
            timeout=10,
        )
        return [
            score.model_dump() for score in response
        ], 0.0  # Cost calculation not implemented for litellm
    except Exception as ex:
        if config["OUTPUT"].getboolean("debug_messages"):
            print("Exception happened " + str(ex))
            # check if the api key is valid
            if os.environ.get("GEMINI_API_KEY") is None:
                print("GEMINI_API_KEY is not set in the environment variables")
            else:
                print(
                    f"GEMINI_API_KEY is set in the environment variables: {os.environ.get('GEMINI_API_KEY')}"
                )
        return [], 0.0


def paper_to_string(paper_entry: Paper) -> str:
    # renders each paper into a string to be processed by GPT
    new_str = (
        "ArXiv ID: "
        + paper_entry.arxiv_id
        + "\n"
        + "Title: "
        + paper_entry.title
        + "\n"
        + "Authors: "
        + " and ".join(paper_entry.authors)
        + "\n"
        + "Abstract: "
        + paper_entry.abstract[:4000]
    )
    return new_str


def batched(items, batch_size):
    # takes a list and returns a list of list with batch_size
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def filter_papers_by_abstract(
    papers, config, client, base_prompt, criterion
) -> List[Paper]:
    filter_postfix = "Identify any papers that are absolutely and completely irrelavent to the criteria, and you are absolutely sure your friend will not enjoy. Return a list of arxiv IDs to filter out. Be extremely cautious, and if you are unsure at all, do not add a paper in this list. You will check it in detail later."
    batches_of_papers = batched(papers, 10)
    final_list = []
    cost = 0
    for batch in batches_of_papers:
        papers_string = "".join([paper_to_abstract(paper) for paper in batch])
        full_prompt = (
            base_prompt + "\n " + criterion + "\n" + papers_string + filter_postfix
        )

        try:
            response = client.chat.completions.create(
                model=config["SELECTION"]["model"],
                messages=[{"role": "user", "content": full_prompt}],
                max_tokens=1024,
                response_model=FilteredPapers,
            )
            filtered_set = set(response.filtered_ids)
            for paper in batch:
                if paper.arxiv_id not in filtered_set:
                    final_list.append(paper)
                else:
                    print("Filtered out paper " + paper.arxiv_id)
        except Exception as ex:
            print("Exception happened " + str(ex))
            if os.environ.get("GEMINI_API_KEY") is None:
                print("GEMINI_API_KEY is not set in the environment variables")
            else:
                print(
                    f"GEMINI_API_KEY is set in the environment variables: {os.environ.get('GEMINI_API_KEY')}"
                )
            continue

    return final_list, cost


def paper_to_abstract(paper_entry: Paper) -> str:
    return (
        "ArXiv ID: "
        + paper_entry.arxiv_id
        + " Title: "
        + paper_entry.title
        + "Abstract: "
        + paper_entry.abstract
        + "\n"
    )


def run_on_batch(paper_batch, base_prompt, criterion, postfix_prompt, client, config):
    batch_str = [paper_to_string(paper) for paper in paper_batch]
    full_prompt = "\n".join(
        [
            base_prompt,
            criterion + "\n",
            "\n\n".join(batch_str) + "\n",
            postfix_prompt,
        ]
    )
    json_dicts, cost = run_and_parse_chatgpt(full_prompt, client, config)
    return json_dicts, cost


def filter_by_gpt(
    all_authors, papers, config, client, all_papers, selected_papers, sort_dict
):
    # deal with config parsing
    with open("paper_assistant/config/base_prompt.txt", "r") as f:
        base_prompt = f.read()
    with open("paper_assistant/config/paper_topics.txt", "r") as f:
        criterion = f.read()
    with open("paper_assistant/config/postfix_prompt.txt", "r") as f:
        postfix_prompt = f.read()
    all_cost = 0
    if config["SELECTION"].getboolean("run_litellm"):
        # filter first by hindex of authors to reduce costs.
        paper_list = filter_papers_by_hindex(all_authors, papers, config)
        if config["OUTPUT"].getboolean("debug_messages"):
            print(str(len(paper_list)) + " papers after hindex filtering")
        cost = 0
        paper_list, cost = filter_papers_by_abstract(
            paper_list, config, client, base_prompt, criterion
        )
        if config["OUTPUT"].getboolean("debug_messages"):
            print(
                str(len(paper_list))
                + " papers after abstract filtering with cost of $"
                + str(cost)
            )
        all_cost += cost

        # batch the remaining papers and invoke GPT
        batch_of_papers = batched(paper_list, int(config["SELECTION"]["batch_size"]))
        scored_batches = []
        for batch in tqdm(batch_of_papers):
            scored_in_batch = []
            json_dicts, cost = run_on_batch(
                batch, base_prompt, criterion, postfix_prompt, client, config
            )
            all_cost += cost
            for jdict in json_dicts:
                if (
                    int(jdict["RELEVANCE"])
                    >= int(config["FILTERING"]["relevance_cutoff"])
                    and jdict["NOVELTY"] >= int(config["FILTERING"]["novelty_cutoff"])
                    and jdict["ARXIVID"] in all_papers
                ):
                    selected_papers[jdict["ARXIVID"]] = {
                        **dataclasses.asdict(all_papers[jdict["ARXIVID"]]),
                        **jdict,
                    }
                    sort_dict[jdict["ARXIVID"]] = jdict["RELEVANCE"] + jdict["NOVELTY"]
                scored_in_batch.append(
                    {
                        **dataclasses.asdict(all_papers[jdict["ARXIVID"]]),
                        **jdict,
                    }
                )
            scored_batches.append(scored_in_batch)
        if config["OUTPUT"].getboolean("dump_debug_file"):
            with open(
                config["OUTPUT"]["output_path"] + "gpt_paper_batches.debug.json", "w"
            ) as outfile:
                json.dump(scored_batches, outfile, cls=EnhancedJSONEncoder, indent=4)
        if config["OUTPUT"].getboolean("debug_messages"):
            print("Total cost: $" + str(all_cost))


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read("configs/config.ini")
    # Initialize the LiteLLM client with Instructor
    client = instructor.from_litellm(completion)

    # deal with config parsing
    with open("paper_assistant/config/base_prompt.txt", "r") as f:
        base_prompt = f.read()
    with open("paper_assistant/config/paper_topics.txt", "r") as f:
        criterion = f.read()
    with open("paper_assistant/config/postfix_prompt.txt", "r") as f:
        postfix_prompt = f.read()
    # loads papers from 'in/debug_papers.json' and filters them
    with open("in/debug_papers.json", "r") as f:
        paper_list_in_dict = json.load(f)
    papers = [
        [
            Paper(
                arxiv_id=paper["arxiv_id"],
                authors=paper["authors"],
                title=paper["title"],
                abstract=paper["abstract"],
            )
            for paper in batch
        ]
        for batch in paper_list_in_dict
    ]
    all_papers = {}
    paper_outputs = {}
    sort_dict = {}
    total_cost = 0
    for batch in tqdm(papers):
        json_dicts, cost = run_on_batch(
            batch, base_prompt, criterion, postfix_prompt, client, config
        )
        total_cost += cost
        for paper in batch:
            all_papers[paper.arxiv_id] = paper
        for jdict in json_dicts:
            paper_outputs[jdict["ARXIVID"]] = {
                **dataclasses.asdict(all_papers[jdict["ARXIVID"]]),
                **jdict,
            }
            sort_dict[jdict["ARXIVID"]] = jdict["RELEVANCE"] + jdict["NOVELTY"]

    print("total cost:" + str(total_cost))
    keys = list(sort_dict.keys())
    values = list(sort_dict.values())

    sorted_keys = [keys[idx] for idx in argsort(values)[::-1]]
    selected_papers = {key: paper_outputs[key] for key in sorted_keys}

    with open(
        config["OUTPUT"]["output_path"] + "filter_paper_test.debug.json", "w"
    ) as outfile:
        json.dump(selected_papers, outfile, cls=EnhancedJSONEncoder, indent=4)
