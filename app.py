from flask import Flask, render_template, jsonify
import json
from datetime import datetime
import configparser
from arxiv_scraper import Paper
import os
import markdown
from qa_processor import QaProcessor
from markdown_processor import MarkdownProcessor

app = Flask(__name__)
qa_processor = QaProcessor()

# Initialize the markdown processor
md_processor = MarkdownProcessor()

@app.route('/')
def index():
    """Main route to display papers"""
    try:
        # Load papers from JSON
        with open('out/output.json', 'r') as f:
            papers_dict = json.load(f)
        
        # Load header content
        with open('configs/header.md', 'r') as f:
            header_content = f.read()
        
        # Convert header markdown to HTML
        header_html = md_processor.process_content(header_content)
        
        # Convert the data structure to match Paper class
        papers = []
        for p in papers_dict.values():
            paper_data = {
                'arxiv_id': p.get('ARXIVID') or p.get('arxiv_id'),
                'title': p['title'],
                'abstract': p['abstract'],
                'authors': p['authors'],
                'url': f"https://arxiv.org/abs/{p.get('ARXIVID') or p.get('arxiv_id')}",
                'comment': p.get('COMMENT') or p.get('comment'),
                'relevance': p.get('RELEVANCE') or p.get('relevance'),
                'novelty': p.get('NOVELTY') or p.get('novelty')
            }
            papers.append(Paper(**paper_data))
        
        # Get current date
        date = datetime.now().strftime("%m/%d/%Y")
        
        # Render template with header content
        return render_template('paper_template.html', 
                             papers=papers, 
                             date=date, 
                             header_content=header_html)
    except Exception as e:
        print(f"Error in index route: {e}")
        return f"Error loading papers: {str(e)}", 500

@app.route('/qa_progress/<arxiv_id>')
def get_qa_progress(arxiv_id):
    """Get the current progress of Q&A generation for a paper"""
    return jsonify(qa_processor.get_progress(arxiv_id))

@app.route('/get_qa/<arxiv_id>')
def get_qa(arxiv_id):
    try:
        # Load the paper data
        with open('out/output.json', 'r') as f:
            papers = json.load(f)
        
        # Find the paper with matching arxiv_id
        paper = None
        for p in papers.values():
            if p.get('ARXIVID', p.get('arxiv_id')) == arxiv_id:
                paper_data = {
                    'arxiv_id': p.get('ARXIVID') or p.get('arxiv_id'),
                    'title': p['title'],
                    'abstract': p['abstract'],
                    'authors': p['authors'],
                    'url': f"https://arxiv.org/abs/{p.get('ARXIVID') or p.get('arxiv_id')}",
                    'comment': p.get('COMMENT') or p.get('comment'),
                    'relevance': p.get('RELEVANCE') or p.get('relevance'),
                    'novelty': p.get('NOVELTY') or p.get('novelty')
                }
                paper = Paper(**paper_data)
                break
        
        if not paper:
            return jsonify({'error': 'Paper not found'})
        
        # Process Q&A
        qa_results = qa_processor.process_qa(paper)
        
        if 'error' in qa_results:
            return jsonify({'error': qa_results['error']})
        
        # Format Q&A with rich formatting
        formatted_content = ""
        for question, answer in qa_results.items():
            # Format each Q&A pair
            qa_section = f"### {question}\n\n{answer}\n\n"
            formatted_content += qa_section
        
        # Process the markdown content
        html_content = md_processor.process_content(formatted_content)
        print(html_content)
        return jsonify({'content': html_content})
        
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    # Load API keys from environment or config
    keyconfig = configparser.ConfigParser()
    keyconfig.read("configs/keys.ini")

    # Set up Gemini API key if using Gemini
    GEMINI_API_KEY = keyconfig["GEMINI"]["api_key"]
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
    app.run(debug=True)
