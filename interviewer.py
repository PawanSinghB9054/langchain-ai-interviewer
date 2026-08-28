from dotenv import load_dotenv
load_dotenv()

from langchain.chat_models import init_chat_model
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.embeddings import init_embeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

##===== for choice =====##
x = int(input("Press 1 for use of PDF and Press 2 for use of normal case... "))

##=== PDF prompt ===##
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

##===== prompt for normal use cases ====##
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

##==== LLM model =====##
model = init_chat_model(
    "mistral-small-latest",
    model_provider="mistralai"
)

##===== Set chains ====##
chain = prompt_2 | model | StrOutputParser()
pdf_chain = pdf_prompt | model | StrOutputParser()

##==== With PDF ====##
if x == 1:

    ## Load pdf
    data = PyPDFLoader("handom.pdf")
    docs = data.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=2500, chunk_overlap=150)
    chunks = splitter.split_documents(docs)

    embeddings = init_embeddings("mistralai:mistral-embed")

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="database"
    )

    retrievers = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4}
    )

    topic = input("Enter Interview Topic : ")
    diff = input("Set Level (Easy , Medium , Hard , Extream) : ")
    history = []

    ## First question — retrieve based on topic
    retrieved_docs = retrievers.invoke(topic)
    context = "\n\n".join([doc.page_content for doc in retrieved_docs])

    que = pdf_chain.invoke({
        "topic": topic,
        "difficulty": diff,
        "context": context,
        "history": history,
        "answer": "Start the interview"
    })

    print("AI : ", que)
    history.append(AIMessage(content=que))

    while True:
        a = input("Enter your ans : ")
        if a.lower() == "exit":
            break

        history.append(HumanMessage(content=a))

        ## Retrieve fresh context based on candidate's answer
        retrieved_docs = retrievers.invoke(a)
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])

        ans = pdf_chain.invoke({
            "topic": topic,
            "difficulty": diff,
            "context": context,
            "history": history,
            "answer": a
        })

        print("AI:", ans)
        history.append(AIMessage(content=ans))

##===== Normal use =====##
if x == 2:
    topic = input("Enter Interview Topic : ")
    diff = input("Set Level (Easy , Medium , Hard , Extream) : ")
    history = []

    que = chain.invoke({
        "topic": topic,
        "difficulty": diff,
        "history": history,
        "answer": "Start the interview"
    })

    print("AI : ", que)
    history.append(AIMessage(content=que))

    while True:
        a = input("Enter your ans : ")
        if a.lower() == "exit":
            break

        history.append(HumanMessage(content=a))

        ans = chain.invoke({
            "topic": topic,
            "difficulty": diff,
            "history": history,
            "answer": a
        })

        print("AI:", ans)
        history.append(AIMessage(content=ans))