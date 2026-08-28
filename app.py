from dotenv import load_dotenv
load_dotenv()
 
import os
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
 
from langchain.chat_models import init_chat_model
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.embeddings import init_embeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
 
app = Flask(__name__)
 
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
 
# ===== In-memory session store (simple, single-user demo) =====
SESSION = {
    "mode": None,        # "pdf" or "normal"
    "topic": None,
    "difficulty": None,
    "history": [],        # list of HumanMessage/AIMessage
    "retriever": None,
}
 
# ===== Prompts (same as your original code) =====
pdf_prompt = ChatPromptTemplate.from_template(
    """
You are a professional AI interviewer.
 
You are taking a {topic} interview at {difficulty} level, based ONLY on the following reference material extracted from a document.
 
Reference Material (use this to form your questions):
{context}
 
Your responsibilities:
- Ask one interview question at a time, strictly based on the reference material above.
- Wait for the candidate's answer.
- Evaluate the candidate's answer.
- Give a score from 1 to 10.
- Give short and clear feedback.
- Ask a follow-up question when appropriate.
- Gradually increase the difficulty.
- Do not reveal the correct answer before the candidate answers.
- Behave like a real interviewer.
 
Previous conversation:
{history}
 
Candidate's latest answer:
{answer}
 
If this is the beginning of the interview, ask the first question.
 
Otherwise, follow this format:
 
Score: X/10
 
Feedback:
<short feedback>
 
Next Question:
<next interview question>
"""
)
 
prompt_2 = ChatPromptTemplate.from_template(
    """
You are a professional AI interviewer.
 
You are taking a {topic} interview at {difficulty} level.
 
Your responsibilities:
- Ask one interview question at a time.
- Wait for the candidate's answer.
- Evaluate the candidate's answer.
- Give a score from 1 to 10.
- Give short and clear feedback.
- Ask a follow-up question when appropriate.
- Gradually increase the difficulty.
- Do not reveal the correct answer before the candidate answers.
- Behave like a real interviewer.
 
Previous conversation:
{history}
 
Candidate's latest answer:
{answer}
 
If this is the beginning of the interview, ask the first question.
 
Otherwise, follow this format:
 
Score: X/10
 
Feedback:
<short feedback>
 
Next Question:
<next interview question>
"""
)
 
model = init_chat_model("mistral-small-latest", model_provider="mistralai")
 
chain = prompt_2 | model | StrOutputParser()
pdf_chain = pdf_prompt | model | StrOutputParser()
 
 
def history_to_text(history):
    """Convert list of messages into plain text for the prompt."""
    lines = []
    for m in history:
        role = "AI" if isinstance(m, AIMessage) else "Candidate"
        lines.append(f"{role}: {m.content}")
    return "\n".join(lines)
 
 
@app.route("/")
def index():
    return render_template("index.html")
 
 
@app.route("/api/start", methods=["POST"])
def start_interview():
    """Start a new interview. Handles both normal and PDF mode."""
    global SESSION
 
    mode = request.form.get("mode")  # "pdf" or "normal"
    topic = request.form.get("topic")
    difficulty = request.form.get("difficulty")
 
    SESSION = {
        "mode": mode,
        "topic": topic,
        "difficulty": difficulty,
        "history": [],
        "retriever": None,
    }
 
    if mode == "pdf":
        pdf_file = request.files.get("pdf")
        if not pdf_file:
            return jsonify({"error": "PDF file is required for PDF mode"}), 400
 
        filename = secure_filename(pdf_file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        pdf_file.save(filepath)
 
        data = PyPDFLoader(filepath)
        docs = data.load()
 
        splitter = RecursiveCharacterTextSplitter(chunk_size=2500, chunk_overlap=150)
        chunks = splitter.split_documents(docs)
 
        embeddings = init_embeddings("mistralai:mistral-embed")
 
        vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory="database"
        )
 
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4}
        )
        SESSION["retriever"] = retriever
 
        retrieved_docs = retriever.invoke(topic)
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
 
        que = pdf_chain.invoke({
            "topic": topic,
            "difficulty": difficulty,
            "context": context,
            "history": "",
            "answer": "Start the interview"
        })
 
    else:  # normal mode
        que = chain.invoke({
            "topic": topic,
            "difficulty": difficulty,
            "history": "",
            "answer": "Start the interview"
        })
 
    SESSION["history"].append(AIMessage(content=que))
    return jsonify({"message": que})
 
 
@app.route("/api/answer", methods=["POST"])
def answer():
    """Send candidate's answer, get next AI response."""
    global SESSION
 
    data = request.get_json()
    ans = data.get("answer", "")
 
    if not SESSION["mode"]:
        return jsonify({"error": "No interview in progress. Start one first."}), 400
 
    SESSION["history"].append(HumanMessage(content=ans))
    history_text = history_to_text(SESSION["history"])
 
    if SESSION["mode"] == "pdf":
        retriever = SESSION["retriever"]
        retrieved_docs = retriever.invoke(ans)
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
 
        reply = pdf_chain.invoke({
            "topic": SESSION["topic"],
            "difficulty": SESSION["difficulty"],
            "context": context,
            "history": history_text,
            "answer": ans
        })
    else:
        reply = chain.invoke({
            "topic": SESSION["topic"],
            "difficulty": SESSION["difficulty"],
            "history": history_text,
            "answer": ans
        })
 
    SESSION["history"].append(AIMessage(content=reply))
    return jsonify({"message": reply})
 
 
@app.route("/api/reset", methods=["POST"])
def reset():
    global SESSION
    SESSION = {"mode": None, "topic": None, "difficulty": None, "history": [], "retriever": None}
    return jsonify({"status": "reset"})
 
 
if __name__ == "__main__":
    app.run(debug=True, port=5000)