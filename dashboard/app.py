import streamlit as st
import requests
import os
import pandas as pd
import sqlite3
from datetime import datetime

st.title("OMR Sheet Evaluator Dashboard")

uploaded_file = st.file_uploader("Upload OMR Sheet Image", type=["jpg", "jpeg", "png"])
rows = st.number_input("Number of Rows", min_value=1, max_value=100, value=5)
cols = st.number_input("Number of Columns", min_value=1, max_value=100, value=20)
answer_key = st.text_input("Answer Key CSV Path", value="answer_keys/SetA_key.csv")

# Store results in session state
if 'results' not in st.session_state:
    st.session_state['results'] = []

if uploaded_file is not None:
    st.image(uploaded_file, caption="Uploaded OMR Sheet", use_column_width=True)
    if st.button("Process OMR Sheet"):
        temp_path = os.path.join("data", "uploads", uploaded_file.name)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        with open(temp_path, "rb") as img_file:
            files = {"image": img_file}
            data = {"rows": rows, "cols": cols, "answer_key": answer_key}
            response = requests.post("http://127.0.0.1:5000/process", files=files, data=data)
        if response.ok:
            result = response.json()
            st.success(f"Score: {result['score']} / {result['total']}")
            st.write("Rotation Angle:", result["rotation_angle"])
            st.write("Grid Coordinates:", result["grid_coords"])
            st.write("Filled Bubble Matrix:")
            st.dataframe(result["bubble_matrix"])
            # Save result for analytics/export
            st.session_state['results'].append({
                'filename': uploaded_file.name,
                'score': result['score'],
                'total': result['total'],
                'rotation_angle': result['rotation_angle'],
                'grid_coords': result['grid_coords']
            })
        else:
            st.error(f"Error: {response.text}")

# Analytics section
if st.session_state['results']:
    st.header("Analytics & Export")
    df = pd.DataFrame(st.session_state['results'])
    st.write("Results Table:")
    st.dataframe(df)
    avg_score = df['score'].mean()
    st.write(f"Average Score: {avg_score:.2f}")
    st.write(f"Highest Score: {df['score'].max()}")
    st.write(f"Lowest Score: {df['score'].min()}")
    # Export
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Results as CSV", data=csv, file_name="omr_results.csv", mime="text/csv")

DB_PATH = "data/omr_results.db"

def get_results():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT filename, score, total, timestamp FROM results ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_audit_log():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT filename, action, timestamp FROM audit_log ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()
    return rows

st.header("OMR Sheet Evaluation Dashboard")
st.subheader("Processed Results (from Database)")
results = get_results()
if results:
    import pandas as pd
    df_results = pd.DataFrame(results, columns=["Filename", "Score", "Total", "Timestamp"])
    st.dataframe(df_results)
    csv = df_results.to_csv(index=False).encode('utf-8')
    st.download_button("Download Results as CSV", csv, "results.csv", "text/csv")
else:
    st.info("No results found in database.")

st.subheader("Audit Log")
audit_log = get_audit_log()
if audit_log:
    df_audit = pd.DataFrame(audit_log, columns=["Filename", "Action", "Timestamp"])
    st.dataframe(df_audit)
else:
    st.info("No audit log entries found.")