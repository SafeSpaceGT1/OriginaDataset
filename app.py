import streamlit as st
import re
import json
from io import StringIO
import docx2txt
import pdfplumber
import os
from datetime import datetime
import shutil

st.title("Mental Health Dataset Creator - Alpha Prototype")
st.write("Upload multiple raw text files to anonymize and structure into prompt/response format for AI training.")

STORAGE_DIR = "saved_datasets"
BACKUP_DIR = "backup_datasets"
VERSION_DIR = "versioned_datasets"
VERSION_LABELS_FILE = "version_labels.json"
os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(VERSION_DIR, exist_ok=True)

if os.path.exists(VERSION_LABELS_FILE):
    with open(VERSION_LABELS_FILE, "r") as f:
        version_labels = json.load(f)
else:
    version_labels = {}

uploaded_files = st.file_uploader("Upload .txt, .pdf, or .docx files (you can select multiple)", type=["txt", "pdf", "docx"], accept_multiple_files=True)
tag_input = st.text_input("Enter a custom tag for this dataset (e.g., grief, trauma, CBT):", value="mental_health")

def scrub_text(text):
    text = re.sub(r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b", "[REDACTED_NAME]", text)
    text = re.sub(r"\d{1,2}/\d{1,2}/\d{2,4}", "[REDACTED_DATE]", text)
    text = re.sub(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", "[REDACTED_PHONE]", text)
    text = re.sub(r"[\w.-]+@[\w.-]+", "[REDACTED_EMAIL]", text)
    return text

def segment_into_pairs(text, tag):
    paragraphs = [p.strip() for p in text.split("\n") if p.strip() != ""]
    dataset = []
    for i in range(0, len(paragraphs)-1, 2):
        dataset.append({"prompt": paragraphs[i], "response": paragraphs[i+1], "tag": tag})
    return dataset

def extract_text(file):
    if file.type == "text/plain":
        return StringIO(file.getvalue().decode("utf-8")).read()
    elif file.type == "application/pdf":
        with pdfplumber.open(file) as pdf:
            return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return docx2txt.process(file)
    return ""

def highlight(text, word):
    return text.replace(word, f"**:orange[{word}]**") if word else text

if uploaded_files:
    combined_text = ""
    for file in uploaded_files:
        raw_text = extract_text(file)
        scrubbed = scrub_text(raw_text)
        combined_text += scrubbed + "\n"

    pairs = segment_into_pairs(combined_text, tag_input)

    st.subheader("Preview (First 3 Entries Across All Files)")
    for entry in pairs[:3]:
        st.json(entry)

    jsonl_data = "\n".join([json.dumps(p) for p in pairs])
    filename_base = f"{tag_input.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    filename = f"{filename_base}.jsonl"
    local_path = os.path.join(STORAGE_DIR, filename)

    with open(local_path, "w", encoding="utf-8") as f:
        f.write(jsonl_data)

    version_path = os.path.join(VERSION_DIR, filename)
    shutil.copy(local_path, version_path)

    version_label = st.text_input("Label this version (e.g., 'v1 baseline', 'v2 with emotion tags'):")
    if version_label:
        version_labels[filename] = version_label
        with open(VERSION_LABELS_FILE, "w") as f:
            json.dump(version_labels, f, indent=2)
        st.success(f"Version labeled: {version_label}")

    st.download_button("Download JSONL Dataset", data=jsonl_data, file_name=filename, mime="text/plain")
