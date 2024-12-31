import configparser
from typing import Dict, List
import arxiv
from arxiv_scraper import Paper
from litellm import completion
import instructor
from pydantic import BaseModel
from markitdown import MarkItDown
import os

class QaResult(BaseModel):
    question: str
    answer: str

class PseudocodeResult(BaseModel):
    code: str

class QaProcessor:
    def __init__(self):
        # Load config
        self.config = configparser.ConfigParser()
        self.config.read("configs/config.ini")
        
        # Initialize client
        self.client = instructor.from_litellm(completion)
        
        # Load questions
        with open("configs/questions.txt", "r") as f:
            self.questions = [line.strip() for line in f.readlines() if line.strip()]
            
        # Progress tracking
        self.progress = {}
    
    def get_paper_content(self, paper: Paper) -> str:
        """Get paper content using arxiv API and markitdown"""
        try:
            search = arxiv.Search(id_list=[paper.arxiv_id])
            results = list(arxiv.Client().results(search))
            if results:
                paper_entry = next(results)
                pdf_filename = f"out/pdfs/{paper.arxiv_id}.pdf"
                os.makedirs("out/pdfs", exist_ok=True)
                paper_entry.download_pdf(filename=pdf_filename)

                md = MarkItDown()
                result = md.convert(pdf_filename)
                return result.text_content
            return None
        except Exception as e:
            print(f"Error getting paper content for {paper.arxiv_id}: {e}")
            return None

    def process_qa(self, paper: Paper, progress_callback=None) -> Dict[str, str]:
        """Process Q&A for a paper with progress tracking"""
        try:
            # Initialize progress
            paper_id = paper.arxiv_id
            self.progress[paper_id] = {'current': 0, 'total': len(self.questions)}
            
            # Get paper content
            text_content = self.get_paper_content(paper)
            if not text_content:
                text_content = paper.abstract  # Fallback to abstract if full text fails
            
            # Process each question
            qa_results = {}
            conversation_history = []

            # rules 
            base_rules = """
            You are a helpful assistant that answers questions about a paper.
            You are given a paper and a question.
            You are to answer the question based on the paper.
            - list as bullet points with markdown formatting.
            - contain important details for each bullet point.
            """
            
            for i, question in enumerate(self.questions, 1):
                try:
                    # Update progress
                    self.progress[paper_id]['current'] = i
                    if progress_callback:
                        progress_callback(paper_id, i, len(self.questions))
                    
                    # Include previous Q&A pairs in the context
                    qa_context = "\n\n".join([
                        f"Q: {q}\nA: {a}" for q, a in qa_results.items()
                    ])

                    # Special handling for the pseudocode question
                    if "Pseudocode" in question or "code block" in question:
                        rules = base_rules + """
                        For the pseudocode implementation:
                        - First determine if the paper proposes a new method that can be implemented
                        - If yes, provide a clear, step-by-step pseudocode implementation
                        - If no, respond with "This paper does not propose a new implementable method."
                        - Use Python-style pseudocode with clear comments
                        - Include the code within a markdown code block
                        """
                        
                        prompt = f"""Paper Content:
                                    {text_content[:50000]}

                                    Task: Analyze if this paper proposes a new method that can be implemented as pseudocode.
                                    If yes, provide a clear implementation. If no, indicate that.

                                    Rules:
                                    {rules}
                                    """
                        
                        # For pseudocode question, don't use the QaResult model
                        try:
                            response = self.client.chat.completions.create(
                                model=self.config["SELECTION"]["model"],
                                messages=[{"role": "user", "content": prompt}],
                            response_model=PseudocodeResult,
                            max_retries=3,
                                timeout=30,
                            )
                            qa_results[question] = response.code
                        except Exception as e:
                            qa_results[question] = f"No pseudocode found given the rules."
                        
                    else:
                        # Normal questions use the standard format
                        prompt = f"""Paper Content:
                                    {text_content[:50000]}

                                    Previous Questions and Answers:
                                    {qa_context}

                                    Current Question: {question}

                                    Rules:
                                    {base_rules}

                                    Please answer the current question, taking into account the previous Q&A if relevant."""

                        response = self.client.chat.completions.create(
                            model=self.config["SELECTION"]["model"],
                            response_model=QaResult,
                            messages=[{"role": "user", "content": prompt}],
                            max_retries=3,
                            timeout=30,
                        )
                        qa_results[question] = response.answer
                    
                except Exception as e:
                    qa_results[question] = f"Error getting answer: {str(e)}"
            
            return qa_results
            
        except Exception as e:
            print(f"Error processing Q&A for paper {paper.arxiv_id}: {e}")
            return {"error": str(e)}
        finally:
            # Clean up progress tracking
            if paper.arxiv_id in self.progress:
                del self.progress[paper.arxiv_id]
    
    def get_progress(self, paper_id: str) -> Dict[str, int]:
        """Get current progress for a paper"""
        return self.progress.get(paper_id, {'current': 0, 'total': 0}) 