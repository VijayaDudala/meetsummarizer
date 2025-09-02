from transformers import pipeline

# Load BART summarizer once
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

def summarize_text(text):
    """
    Summarize a long text into bullet points using BART.
    Returns a list of bullet points.
    """
    if not text or text.strip() == "":
        return ["No text to summarize"]

    # Break text into chunks if it's very long
    max_chunk = 1000
    chunks = [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)]

    bullet_points = []
    for chunk in chunks:
        summary = summarizer(chunk, max_length=160, min_length=25, do_sample=False)
        bullet_points.append(summary[0]['summary_text'])

    # Convert to bullet list (split sentences)
    final_points = []
    for point in bullet_points:
        sentences = point.split(". ")
        for s in sentences:
            if s.strip():
                final_points.append(s.strip())

    return final_points
