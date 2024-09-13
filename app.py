import streamlit as st
import openai
from PyPDF2 import PdfReader
from langdetect import detect
from pymongo import MongoClient
from bson.objectid import ObjectId


# OpenAI API-Schlüssel setzen
openai.api_key = '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'  

# Verbindung zur MongoDB herstellen
def get_database():
    CONNECTION_STRING = "mongodb://localhost:27017"
    client = MongoClient(CONNECTION_STRING)
    return client['transcript_analysis_db']

db = get_database()
collection = db['analyses']

# Funktion zum Extrahieren von Text aus PDF
def extract_text_from_pdf(pdf_file):
    pdf_reader = PdfReader(pdf_file)
    text = ''
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# Sprache erkennen
def analyze_transcript(text, language):
    if language == 'de':
        messages = [
            {"role": "system", "content": "Du bist ein hilfreicher Assistent, der deutsche Texte analysiert und wichtige Erkenntnisse extrahiert."},
            {"role": "user", "content": f"Analysiere folgendes deutsche Transkript und extrahiere wichtige Erkenntnisse:\n\n{text}"}
        ]
    else:
        messages = [
            {"role": "system", "content": "You are a helpful assistant that analyzes English texts and extracts key insights."},
            {"role": "user", "content": f"Analyze the following English transcript and extract key insights:\n\n{text}"}
        ]
    
    response = openai.ChatCompletion.create(
        model='gpt-4',  # Stellen Sie sicher, dass Sie Zugriff auf GPT-4 haben
        messages=messages,
        max_tokens=1500,
        n=1,
        stop=None,
        temperature=0.7,
    )
    return response.choices[0].message['content'].strip()


# Hauptfunktion der Streamlit-App
def main():
    st.title("Transkript Analyse Tool")
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Wählen Sie eine Seite", ["Transkripte hochladen", "Weitere Analysen", "Analysen anzeigen"])


   uploaded_file = st.file_uploader("Laden Sie ein Transkript im PDF-Format hoch", type=["pdf"])

    if uploaded_files:
    processing_option = st.radio("Verarbeitungsoption wählen:", ("Einzeln verarbeiten", "Gemeinsam verarbeiten"))

    if st.button("Analyse starten"):
        with st.spinner("Analysiere Transkripte..."):
            analyses = []
            if processing_option == "Einzeln verarbeiten":
                for uploaded_file in uploaded_files:
                    text = extract_text_from_pdf(uploaded_file)
                    language = detect(text)
                    st.write(f"Transkript: {uploaded_file.name} - Erkannte Sprache: {'Deutsch' if language == 'de' else 'Englisch'}")

                    analysis = analyze_transcript(text, language)
                    st.success(f"Analyse von {uploaded_file.name} abgeschlossen!")
                    st.subheader(f"Analyseergebnisse für {uploaded_file.name}:")
                    st.write(analysis)

                    # Ergebnisse in MongoDB speichern
                    data = {
                        'transcript_name': uploaded_file.name,
                        'language': language,
                        'analysis': analysis
                    }
                    collection.insert_one(data)
                    st.info(f"Ergebnisse für {uploaded_file.name} wurden in der Datenbank gespeichert.")

            elif processing_option == "Gemeinsam verarbeiten":
                texts = []
                languages = set()
                for uploaded_file in uploaded_files:
                    text = extract_text_from_pdf(uploaded_file)
                    texts.append(text)
                    language = detect(text)
                    languages.add(language)

                if len(languages) > 1:
                    st.error("Alle Transkripte müssen die gleiche Sprache haben, um sie gemeinsam zu verarbeiten.")
                else:
                    combined_text = "\n".join(texts)
                    language = languages.pop()
                    st.write(f"Erkannte Sprache: {'Deutsch' if language == 'de' else 'Englisch'}")

                    analysis = analyze_transcript(combined_text, language)
                    st.success("Gemeinsame Analyse abgeschlossen!")
                    st.subheader("Analyseergebnisse der gemeinsamen Transkripte:")
                    st.write(analysis)

                    # Ergebnisse in MongoDB speichern
                    data = {
                        'transcript_name': ", ".join([file.name for file in uploaded_files]),
                        'language': language,
                        'analysis': analysis
                    }
                    collection.insert_one(data)
                    st.info("Gemeinsame Analyseergebnisse wurden in der Datenbank gespeichert.")

st.header("Weitere Analysen basierend auf bisherigen Ergebnissen")

# Abrufen aller Analysen aus der Datenbank
all_analyses = list(collection.find())

if all_analyses:
    st.subheader("Verfügbare Analysen:")
    analysis_options = {str(a['_id']): f"{a['transcript_name']} - {a.get('question', 'Initiale Analyse')}" for a in all_analyses}
    selected_analysis_ids = st.multiselect("Wählen Sie Analysen für die weitere Verarbeitung aus:", options=list(analysis_options.keys()), format_func=lambda x: analysis_options[x])

    if selected_analysis_ids:
        selected_analyses = [collection.find_one({'_id': ObjectId(_id)})['analysis'] for _id in selected_analysis_ids]
        new_question = st.text_area("Geben Sie eine neue Frage ein:")
        if st.button("Neue Analyse durchführen"):
            with st.spinner("Analysiere basierend auf den ausgewählten Analysen..."):
                combined_analysis_text = "\n".join(selected_analyses)
                language = detect(combined_analysis_text)
                st.write(f"Erkannte Sprache der kombinierten Analysen: {'Deutsch' if language == 'de' else 'Englisch'}")

                # Neuen Prompt erstellen und Analyse durchführen
                if language == 'de':
                    messages = [
                        {"role": "system", "content": "Du bist ein hilfreicher Assistent."},
                        {"role": "user", "content": f"{new_question}\n\nBasisinformationen:\n{combined_analysis_text}"}
                    ]
                else:
                    messages = [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": f"{new_question}\n\nBase information:\n{combined_analysis_text}"}
                    ]

                response = openai.ChatCompletion.create(
                    model='gpt-4',
                    messages=messages,
                    max_tokens=1500,
                    n=1,
                    stop=None,
                    temperature=0.7,
                )
                new_analysis = response.choices[0].message['content'].strip()
                st.success("Neue Analyse abgeschlossen!")
                st.subheader("Ergebnisse der neuen Analyse:")
                st.write(new_analysis)

                # Neues Analyseergebnis speichern
                data = {
                    'transcript_name': "Weitere Analyse",
                    'language': language,
                    'analysis': new_analysis,
                    'based_on_ids': selected_analysis_ids,
                    'question': new_question
                }
                collection.insert_one(data)
                st.info("Neue Analyseergebnisse wurden in der Datenbank gespeichert.")
else:
    st.info("Es sind noch keine Analysen verfügbar.")





if __name__ == "__main__":
    main()
