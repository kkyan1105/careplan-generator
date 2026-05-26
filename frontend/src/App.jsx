import { useState, useEffect, useRef } from "react";

const INITIAL_FORM = {
  patient_first_name: "",
  patient_last_name: "",
  patient_mrn: "",
  primary_diagnosis: "",
  additional_diagnoses: "",
  referring_provider_name: "",
  referring_provider_npi: "",
  medication_name: "",
  medication_history: "",
  patient_records: "",
};

const styles = {
  page: { maxWidth: 780, margin: "40px auto", fontFamily: "system-ui, sans-serif", padding: "0 20px" },
  heading: { fontSize: 22, fontWeight: 700, marginBottom: 24 },
  section: { marginBottom: 24 },
  sectionTitle: { fontSize: 13, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1, color: "#555", marginBottom: 12 },
  row: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 14 },
  field: { display: "flex", flexDirection: "column", gap: 4 },
  label: { fontSize: 13, color: "#333", fontWeight: 500 },
  input: { padding: "8px 10px", border: "1px solid #ccc", borderRadius: 6, fontSize: 14 },
  textarea: { padding: "8px 10px", border: "1px solid #ccc", borderRadius: 6, fontSize: 14, resize: "vertical", minHeight: 80 },
  button: { padding: "10px 28px", background: "#1a56db", color: "#fff", border: "none", borderRadius: 6, fontSize: 15, fontWeight: 600, cursor: "pointer" },
  buttonDisabled: { padding: "10px 28px", background: "#93b4f5", color: "#fff", border: "none", borderRadius: 6, fontSize: 15, fontWeight: 600, cursor: "not-allowed" },
  resultBox: { background: "#f4f7ff", border: "1px solid #c5d5f8", borderRadius: 8, padding: 24, marginTop: 32, whiteSpace: "pre-wrap", lineHeight: 1.7, fontSize: 14 },
  resultHeading: { fontSize: 16, fontWeight: 700, marginBottom: 16, color: "#1a56db" },
  error: { color: "#c0392b", marginTop: 12, fontSize: 14 },
  polling: { color: "#555", marginTop: 12, fontSize: 14 },
};

function Field({ label, name, value, onChange, type = "text" }) {
  return (
    <div style={styles.field}>
      <label style={styles.label}>{label}</label>
      <input style={styles.input} type={type} name={name} value={value} onChange={onChange} />
    </div>
  );
}

const POLL_INTERVAL = 3000;

export default function App() {
  const [form, setForm] = useState(INITIAL_FORM);
  const [loading, setLoading] = useState(false);
  const [carePlan, setCarePlan] = useState(null);
  const [error, setError] = useState(null);
  const [pollStatus, setPollStatus] = useState(null); // "pending" | "completed" | "failed" | null
  const intervalRef = useRef(null);

  function stopPolling() {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }

  useEffect(() => {
    return () => stopPolling();
  }, []);

  function startPolling(careplanId) {
    intervalRef.current = setInterval(async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/careplan/${careplanId}/status/`);
        if (!res.ok) throw new Error("Status check failed");
        const data = await res.json();

        setPollStatus(data.status);

        if (data.status === "completed") {
          stopPolling();
          setCarePlan(data.content);
          setLoading(false);
        } else if (data.status === "failed") {
          stopPolling();
          setError("Care plan generation failed. Please try again.");
          setLoading(false);
        }
      } catch (err) {
        stopPolling();
        setError("Lost connection while waiting for results.");
        setLoading(false);
      }
    }, POLL_INTERVAL);
  }

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    stopPolling();
    setLoading(true);
    setError(null);
    setCarePlan(null);
    setPollStatus(null);

    const payload = {
      ...form,
      additional_diagnoses: form.additional_diagnoses
        ? form.additional_diagnoses.split(",").map((s) => s.trim())
        : [],
      medication_history: form.medication_history
        ? form.medication_history.split(",").map((s) => s.trim())
        : [],
    };

    try {
      const res = await fetch("http://localhost:8000/api/careplan/generate/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      setPollStatus("pending");
      startPolling(data.careplan_id);
    } catch (err) {
      setError("Failed to submit. Is the backend running?");
      setLoading(false);
    }
  }

  const isWorking = loading;

  return (
    <div style={styles.page}>
      <div style={styles.heading}>Care Plan Generator</div>

      <form onSubmit={handleSubmit}>
        <div style={styles.section}>
          <div style={styles.sectionTitle}>Patient</div>
          <div style={styles.row}>
            <Field label="First Name" name="patient_first_name" value={form.patient_first_name} onChange={handleChange} />
            <Field label="Last Name" name="patient_last_name" value={form.patient_last_name} onChange={handleChange} />
          </div>
          <div style={styles.row}>
            <Field label="MRN" name="patient_mrn" value={form.patient_mrn} onChange={handleChange} />
            <Field label="Primary Diagnosis (ICD-10)" name="primary_diagnosis" value={form.primary_diagnosis} onChange={handleChange} />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Additional Diagnoses (comma-separated ICD-10 codes)</label>
            <input style={styles.input} name="additional_diagnoses" value={form.additional_diagnoses} onChange={handleChange} />
          </div>
        </div>

        <div style={styles.section}>
          <div style={styles.sectionTitle}>Referring Provider</div>
          <div style={styles.row}>
            <Field label="Provider Name" name="referring_provider_name" value={form.referring_provider_name} onChange={handleChange} />
            <Field label="NPI" name="referring_provider_npi" value={form.referring_provider_npi} onChange={handleChange} />
          </div>
        </div>

        <div style={styles.section}>
          <div style={styles.sectionTitle}>Medication</div>
          <div style={styles.row}>
            <Field label="Medication Name" name="medication_name" value={form.medication_name} onChange={handleChange} />
            <div style={styles.field}>
              <label style={styles.label}>Prior Medication History (comma-separated)</label>
              <input style={styles.input} name="medication_history" value={form.medication_history} onChange={handleChange} />
            </div>
          </div>
        </div>

        <div style={styles.section}>
          <div style={styles.sectionTitle}>Patient Records / Notes</div>
          <div style={styles.field}>
            <label style={styles.label}>Paste any relevant notes or records here</label>
            <textarea style={styles.textarea} name="patient_records" value={form.patient_records} onChange={handleChange} />
          </div>
        </div>

        <button type="submit" style={isWorking ? styles.buttonDisabled : styles.button} disabled={isWorking}>
          {isWorking ? "Generating care plan…" : "Generate Care Plan"}
        </button>

        {isWorking && pollStatus === "pending" && (
          <div style={styles.polling}>Waiting for worker… checking every 3 seconds.</div>
        )}

        {error && <div style={styles.error}>{error}</div>}
      </form>

      {carePlan && (
        <div style={styles.resultBox}>
          <div style={styles.resultHeading}>Generated Care Plan</div>
          {carePlan}
        </div>
      )}
    </div>
  );
}
