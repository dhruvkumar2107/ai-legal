# app.py (cleaned & corrected)
import os
from dotenv import load_dotenv
import streamlit as st

# -------------------------
# Load .env immediately
# -------------------------
here = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(here, ".env")
load_dotenv(dotenv_path=dotenv_path)

# ONE page config (only once)
st.set_page_config(page_title="NyaySathi — Legal AI", layout="wide")

# -------------------------
# Ensure API key is present
# -------------------------
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    st.title("NyaySathi — Legal AI")
    st.error(
        "GEMINI_API_KEY not found. Add `GEMINI_API_KEY=YOUR_KEY` to a .env file in the project root, "
        "then restart the app."
    )
    st.stop()

# -------------------------
# Import local modules AFTER .env loaded
# -------------------------
import llm
import nearby
import utils

# Configure genai in llm module
llm.configure_genai(API_KEY)

# -------------------------
# App UI
# -------------------------
st.title("🧑‍⚖️ NyaySathi — Legal AI (Modular)")

# Sidebar: settings and page selector
with st.sidebar:
    st.header("Settings")
    ui_lang = st.selectbox(
        "Interface language / user language",
        ["English", "Hindi", "Kannada", "Marathi", "Tamil", "Telugu", "Bengali", "Gujarati"],
        index=0,
    )
    anonymous_mode = st.checkbox("Anonymous mode (don't ask personal info)", value=False)
    page = st.radio("Page", ["Analyze", "Nearby Services", "Settings"], index=0)
    st.markdown("---")
    st.text("Pincode / City (for Nearby page):")
    location_hint = st.text_input("Pincode/City", value="")
    max_results = st.slider("Results per category", 1, 10, 5)

# -------------------------
# Analyze page
# -------------------------
# -------------------------
# Analyze page
# -------------------------
if page == "Analyze":
    st.subheader("Describe your issue")
    user_text = st.text_area("Write your legal issue (or paste)", height=220)
    chosen_cat = st.selectbox(
        "Category (optional)",
        ["—", "Domestic violence", "Cybercrime", "Accident", "Consumer", "Employment",
         "Property", "Harassment", "Dowry harassment", "Other"],
    )
    uploaded_files = st.file_uploader("Upload evidence files (optional)", accept_multiple_files=True)

    # ---- session state to persist results across reruns ----
    if "analysis_parsed" not in st.session_state:
        st.session_state.analysis_parsed = None
    if "analysis_raw" not in st.session_state:
        st.session_state.analysis_raw = None

    if st.button("Analyze & Generate Documents"):
        # Validate input
        if not user_text.strip() and (not chosen_cat or chosen_cat == "—"):
            st.error("Provide a description or choose a category.")
            st.stop()

        # Translate input to English for the LLM if UI language isn't English
        input_for_model = user_text
        if ui_lang != "English":
            input_for_model = utils.translate_text(user_text, "English")

        # Build prompt and call LLM
        prompt = llm.build_prompt(input_for_model, ui_lang, anonymous_mode, location_hint)
        with st.spinner("Contacting model and generating outputs..."):
            raw = llm.call_gemini(prompt)
            parsed = llm.extract_json_from_text(raw)

            # Save to session_state so we can render after reruns
            st.session_state.analysis_raw = raw
            st.session_state.analysis_parsed = parsed

            # handle error-in-JSON case immediately so user sees message
            if parsed and isinstance(parsed, dict) and "error" in parsed:
                st.error(f"Gemini API error: {parsed['error']}")
                st.code(raw)
                st.stop()

            if not parsed:
                st.error("Model did not return valid JSON. See raw output below.")
                st.code(raw)
                st.stop()

    # ---- render last successful analysis, if any ----
    parsed = st.session_state.analysis_parsed
    raw = st.session_state.analysis_raw

    if parsed:
        # Render presentation_markdown if provided by model
        pres_md = parsed.get("presentation_markdown")
        if pres_md:
            if ui_lang != "English":
                pres_md = utils.translate_text(pres_md, ui_lang)
            st.markdown(pres_md, unsafe_allow_html=True)
        else:
            # Fallback summary
            st.header("Legal Advice (summary)")
            short_sum = parsed.get("short_summary", "")
            if ui_lang != "English":
                short_sum = utils.translate_text(short_sum, ui_lang)
            st.write(short_sum)

        # Relevant laws
        st.markdown("### Relevant Laws")
        laws = parsed.get("relevant_laws", []) or []
        if laws:
            for law in laws:
                sec = law.get("section") or law.get("name") or ""
                brief = law.get("brief") or ""
                if ui_lang != "English":
                    brief = utils.translate_text(brief, ui_lang)
                st.markdown(f"- **{sec}** — {brief}")
        else:
            st.write("No relevant laws returned.")

        # Action plan
        st.markdown("### Step-by-step Action Plan")
        action_plan = parsed.get("action_plan", []) or []
        if action_plan:
            for i, step in enumerate(action_plan, start=1):
                step_text = step
                if ui_lang != "English":
                    step_text = utils.translate_text(step_text, ui_lang)
                st.markdown(f"{i}. {step_text}")
        else:
            st.write("No action plan returned.")

        # Drafts
        drafts = parsed.get("drafts") or {}
        if drafts:
            st.markdown("### Drafts")
            for name, content in drafts.items():
                val = content or ""
                if ui_lang != "English":
                    val = utils.translate_text(val, ui_lang)
                with st.expander(name):
                    edited = st.text_area(
                        f"Edit {name}", value=val, height=220, key=f"draft_{name}"
                    )
                    st.download_button(
                        f"Download {name}", edited, file_name=f"{name}.txt"
                    )

        # Evidence checklist
        st.markdown("### Evidence Checklist")
        evidence = parsed.get("evidence_checklist", []) or []
        if evidence:
            for ev in evidence:
                ev_text = ev
                if ui_lang != "English":
                    ev_text = utils.translate_text(ev_text, ui_lang)
                # different keys so each checkbox is independent & sticky
                st.checkbox(ev_text, key=f"ev_{hash(ev_text)}")
        else:
            st.write("No evidence suggestions.")

        # Quick sidebar summary
        st.sidebar.markdown("### Quick Info")
        st.sidebar.metric("Case Type", parsed.get("case_type", "Unknown"))
        st.sidebar.metric("Severity (1-10)", parsed.get("severity", 0))


# -------------------------
# Nearby Services page
# -------------------------
elif page == "Nearby Services":
    st.subheader("Nearby Services")
    if not location_hint.strip():
        st.info("Enter a pincode or city in the sidebar to search nearby services.")
    else:
        geo = nearby.geocode_location(location_hint)
        if not geo:
            st.error("Could not geocode that location. Try '560001 Bengaluru' or a city name.")
        else:
            lat, lon, addr = geo["lat"], geo["lon"], geo["address"]
            st.success(f"Found location: {addr} ({lat:.5f}, {lon:.5f})")

            categories = {
                "Police Stations": "police station",
                "Law Firms / Lawyers": "law firm",
                "NGOs / Helplines": "NGO",
                "Hospitals": "hospital",
            }

            import pandas as pd
            for title, q in categories.items():
                st.markdown(f"### {title}")
                hits = nearby.nearby_search(q, lat, lon, limit=max_results)
                if not hits:
                    st.write("No results found (try a nearby city or use Google Places API).")
                    continue
                df = pd.DataFrame(hits)
                for idx, row in df.iterrows():
                    st.markdown(f"**{idx+1}.** {row['name']}  \n{row['address']}  \nDistance: {row['distance_km']} km")
                if not df.empty:
                    st.map(df.rename(columns={"lat": "lat", "lon": "lon"})[["lat", "lon"]])
                    st.download_button(f"Download {title} (CSV)", df.to_csv(index=False), file_name=f"{title.replace(' ', '_')}.csv")

# -------------------------
# Settings / Debug page
# -------------------------
else:
    st.header("Settings / Debug")
    st.write("Project root:", os.getcwd())
    st.write(".env present:", os.path.exists(os.path.join(os.path.dirname(__file__), ".env")))
    st.write("GEMINI_API_KEY loaded length:", len(os.getenv("GEMINI_API_KEY") or ""))
    st.write("Modules loaded: llm, nearby, utils")
