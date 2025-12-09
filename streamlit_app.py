import streamlit as st
from cv_analyzer_backend import CVAnalyzer
import json
from io import BytesIO

# Page config
st.set_page_config(
    page_title="CV Analyzer - HR Assistant",
    page_icon="📄",
    layout="wide"
)

# Translations dictionary
TRANSLATIONS = {
    'pl': {
        'title': '📄 Analizator CV - Asystent HR',
        'config_header': '⚙️ Konfiguracja',
        'language': 'Język interfejsu',
        'select_model': 'Wybierz model LLM',
        'output_format': 'Format wyjściowy',
        'tip': '💡 **Wskazówka:** Przeciągnij i upuść plik CV lub kliknij "Przeglądaj pliki"',
        'upload_cv': '📤 Prześlij CV',
        'choose_file': 'Wybierz plik CV',
        'supported_formats': 'Obsługiwane formaty: PDF, DOCX, DOC, JPG, PNG',
        'file_uploaded': '✅ Przesłano plik:',
        'filename': 'Nazwa pliku',
        'filetype': 'Typ pliku',
        'filesize': 'Rozmiar pliku',
        'client_req': '📝 Wymagania klienta',
        'enter_req': 'Wprowadź wymagania dotyczące stanowiska',
        'default_req': 'Wymagania dla stanowiska Senior Python Developer:\n- Min. 5 lat doświadczenia w Python\n- Znajomość frameworków: Django, Flask lub FastAPI\n- Doświadczenie z bazami danych (SQL, PostgreSQL)\n- Znajomość Docker i CI/CD\n- Doświadczenie w pracy z REST API\n- Mile widziana znajomość AI/ML',
        'req_help': 'Opisz wymagania dotyczące stanowiska i pożądany profil kandydata',
        'custom_prompt': '🎯 Niestandardowy prompt (opcjonalnie)',
        'advanced': 'Zaawansowane: Dostosuj prompt analizy',
        'use_custom': 'Użyj niestandardowego prompta',
        'custom_template': 'Szablon niestandardowego prompta',
        'prompt_help': 'Użyj {cv_text} i {client_requirements} jako zastępczych',
        'analyze_btn': '🚀 Analizuj CV',
        'download_btn': '📥 Pobierz raport',
        'upload_warning': '⚠️ Proszę przesłać plik CV i podać wymagania klienta',
        'analyzing': '🔍 Analizowanie CV... To może chwilę potrwać...',
        'error_extract': '❌ Błąd ekstrakcji tekstu:',
        'text_extracted': '✅ Wyodrębniono tekst z CV:',
        'characters': 'znaków',
        'analysis_failed': '❌ Analiza nie powiodła się:',
        'view_raw': 'Pokaż surową odpowiedź LLM',
        'analysis_complete': '✅ Analiza zakończona pomyślnie!',
        'error': '❌ Błąd:',
        'results_header': '📊 Wyniki analizy',
        'tab_structured': '📋 Widok strukturalny',
        'tab_json': '🔍 Szczegółowy JSON',
        'tab_text': '📄 Wyodrębniony tekst',
        'remotework': 'Praca zdalna',  # ← DODAJ
        'availability': 'Dostępność',
        'basic_info': '👤 Informacje podstawowe',
        'name': 'Imię i nazwisko',
        'email': 'Email',
        'phone': 'Telefon',
        'location_avail': '📍 Lokalizacja i dostępność',
        'location': 'Lokalizacja',
        'remote_work': 'Praca zdalna',
        'availability': 'Dostępność',
        'summary': '💼 Podsumowanie kandydata',
        'tech_stack': '💻 Stack technologiczny',
        'languages_prog': '**Języki programowania:**',
        'frameworks': '**Frameworki:**',
        'databases': '**Bazy danych:**',
        'tools': '**Narzędzia:**',
        'fit_assessment': '🎯 Ocena dopasowania',
        'match_level': 'Poziom dopasowania',
        'recommendation': 'Rekomendacja',
        'justification': '**Uzasadnienie:**',
        'key_strengths': '**Kluczowe mocne strony:**',
        'extracted_text': 'Wyodrębniony tekst z CV',
        'download_pdf': '📥 Pobierz raport PDF',
        'download_docx': '📥 Pobierz raport DOCX',
        'download_json': '📥 Pobierz raport JSON',
        'footer': 'Stworzone z ❤️ przy użyciu Streamlit & Ollama | 2025',
        'basicinfo': 'Informacje podstawowe',
        'locationavail': 'Lokalizacja i dostępność',
        'summary': 'Podsumowanie kandydata',
        'techstack': 'Stack technologiczny',
        'languagesprog': 'Języki programowania',
        'frameworks': 'Frameworki',
        'databases': 'Bazy danych',
        'tools': 'Narzędzia',
        'fitassessment': 'Ocena dopasowania',
        'matchlevel': 'Poziom dopasowania',
        'recommendation': 'Rekomendacja',
        'justification': 'Uzasadnienie',
        'keystrengths': 'Kluczowe mocne strony',        
        'aitab': '🤖 AI Assistant / Asystent AI',
        'ait_tab1': '📝 Korekta tekstu',
        'ait_tab2': '✨ Generowanie treści',
        'ait_selectdata': 'Wybierz dane:',
        'ait_techstack': 'Stack Technologiczny',
        'ait_experience': 'Doświadczenie',
        'ait_skills': 'Umiejętności',
        'ait_description': 'Opis',
        'ait_instruction': 'Instrukcja:',
        'ait_btn_tasks': '📋 Opis zadań',
        'ait_btn_profile': '👤 Profil',
        'ait_btn_justify': '✅ Uzasadnienie',
        'ait_placeholder': "np. 'Opisz zadania na podstawie stacku'",
        'ait_generate': 'Generuj',
        'ait_generating': 'Generowanie...',
        'ait_warning': 'Podaj instrukcję i wybierz dane!',
        'ait_result': 'Wynik:',
        'ait_prompt_tasks': 'Na podstawie stacku opisz szczegółowe zadania programisty',
        'ait_prompt_profile': 'Wygeneruj zwięzły opis profilu kandydata (3-4 zdania)',
        'ait_prompt_justify': 'Uzasadnij, dlaczego ten kandydat pasuje na stanowisko',
    },
    'en': {
        'title': '📄 CV Analyzer - HR Assistant',
        'config_header': '⚙️ Configuration',
        'language': 'Interface Language',
        'select_model': 'Select LLM Model',
        'output_format': 'Output Format',
        'tip': '💡 **Tip:** Drag and drop your CV file or click "Browse files"',
        'upload_cv': '📤 Upload CV',
        'choose_file': 'Choose a CV file',
        'supported_formats': 'Supported formats: PDF, DOCX, DOC, JPG, PNG',
        'file_uploaded': '✅ File uploaded:',
        'remotework': 'Praca zdalna',  # ← DODAJ
        'availability': 'Dostępność',
        'filename': 'Filename',
        'filetype': 'FileType',
        'filesize': 'FileSize',
        'client_req': '📝 Client Requirements',
        'enter_req': 'Enter job requirements',
        'default_req': 'Requirements for Senior Python Developer:\n- Min. 5 years experience in Python\n- Knowledge of Django, Flask or FastAPI\n- Experience with SQL databases\n- Docker and CI/CD knowledge\n- REST API experience\n- AI/ML knowledge is a plus',
        'req_help': 'Describe the job requirements and desired candidate profile',
        'custom_prompt': '🎯 Custom Prompt (Optional)',
        'advanced': 'Advanced: Customize Analysis Prompt',
        'use_custom': 'Use custom prompt',
        'custom_template': 'Custom Prompt Template',
        'prompt_help': 'Use {cv_text} and {client_requirements} as placeholders',
        'analyze_btn': '🚀 Analyze CV',
        'download_btn': '📥 Download Report',
        'upload_warning': '⚠️ Please upload a CV file and provide client requirements',
        'analyzing': '🔍 Analyzing CV... This may take a moment...',
        'error_extract': '❌ Text extraction error:',
        'text_extracted': '✅ CV text extracted:',
        'characters': 'characters',
        'analysis_failed': '❌ Analysis failed:',
        'view_raw': 'View raw LLM response',
        'analysis_complete': '✅ Analysis completed successfully!',
        'error': '❌ Error:',
        'results_header': '📊 Analysis Results',
        'tab_structured': '📋 Structured View',
        'tab_json': '🔍 Detailed JSON',
        'tab_text': '📄 Extracted Text',
        'basic_info': '👤 Basic Information',
        'name': 'Name',
        'email': 'Email',
        'phone': 'Phone',
        'location_avail': '📍 Location & Availability',
        'location': 'Location',
        'remote_work': 'Remote Work',
        'availability': 'Availability',
        'summary': '💼 Candidate Summary',
        'tech_stack': '💻 Technology Stack',
        'languages_prog': '**Programming Languages:**',
        'frameworks': '**Frameworks:**',
        'databases': '**Databases:**',
        'tools': '**Tools:**',
        'fit_assessment': '🎯 Fit Assessment',
        'match_level': 'Match Level',
        'recommendation': 'Recommendation',
        'justification': '**Justification:**',
        'key_strengths': '**Key Strengths:**',
        'extracted_text': 'Extracted CV Text',
        'download_pdf': '📥 Download PDF Report',
        'download_docx': '📥 Download DOCX Report',
        'download_json': '📥 Download JSON Report',
        'footer': 'Made with ❤️ using Streamlit & Ollama | 2025',
        'basicinfo': 'Basic Information',  # ← DODAJ
        'locationavail': 'Location & Availability',  # ← DODAJ
        'summary': 'Candidate Summary',  # ← DODAJ
        'techstack': 'Technology Stack',  # ← DODAJ
        'languagesprog': 'Programming Languages',  # ← DODAJ
        'frameworks': 'Frameworks',  # ← DODAJ
        'databases': 'Databases',  # ← DODAJ
        'tools': 'Tools',  # ← DODAJ
        'fitassessment': 'Fit Assessment',  # ← DODAJ
        'matchlevel': 'Match Level',  # ← DODAJ
        'recommendation': 'Recommendation',  # ← DODAJ
        'justification': 'Justification',  # ← DODAJ
        'keystrengths': 'Key Strengths',
        'aitab': '🤖 AI Assistant',
        'ait_tab1': '📝 Text Correction',
        'ait_tab2': '✨ Content Generation',
        'ait_selectdata': 'Select data:',
        'ait_techstack': 'Tech Stack',
        'ait_experience': 'Experience',
        'ait_skills': 'Skills',
        'ait_description': 'Description',
        'ait_instruction': 'Instruction:',
        'ait_btn_tasks': '📋 Task Description',
        'ait_btn_profile': '👤 Profile',
        'ait_btn_justify': '✅ Justification',
        'ait_placeholder': "e.g. 'Describe programmer tasks based on tech stack'",
        'ait_generate': 'Generate',
        'ait_generating': 'Generating...',
        'ait_warning': 'Provide instruction and select data!',
        'ait_result': 'Result:',
        'ait_prompt_tasks': 'Based on the tech stack, describe detailed programmer tasks',
        'ait_prompt_profile': 'Generate a concise candidate profile description (3-4 sentences)',
        'ait_prompt_justify': 'Justify why this candidate is suitable for the position',
    }
}

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .section-header {
        font-size: 1.5rem;
        color: #2c3e50;
        border-bottom: 2px solid #1f77b4;
        padding-bottom: 0.5rem;
        margin-top: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'cv_text' not in st.session_state:
    st.session_state.cv_text = None
if 'ui_language' not in st.session_state:
    st.session_state.ui_language = 'pl'

# Sidebar Configuration
with st.sidebar:
    st.header(TRANSLATIONS[st.session_state.ui_language]['config_header'])
    
    # Language selector (ALREADY EXISTS)
    ui_language = st.selectbox(
        TRANSLATIONS[st.session_state.ui_language]['language'],
        options=['pl', 'en'],
        format_func=lambda x: '🇵🇱 Polski' if x == 'pl' else '🇬🇧 English',
        index=0 if st.session_state.ui_language == 'pl' else 1,
        key='language_selector'
    )
    
    # Update language in session state
    if ui_language != st.session_state.ui_language:
        st.session_state.ui_language = ui_language
        st.rerun()
    
    t = TRANSLATIONS[ui_language]
    
    # Model selection (ALREADY EXISTS)
    model_name = "qwen2.5:14b"
    
    # Output format (ALREADY EXISTS)
    output_format = st.radio(
        t['output_format'],
        ["PDF", "DOCX"],
        index=0
    )
    
    st.markdown("---")
    
    # Output language (ALREADY EXISTS)
    output_language = st.radio(
        "📄 " + ("Język wyjściowy raportu" if ui_language == 'pl' else "Output Report Language"),
        options=['auto', 'pl', 'en'],
        format_func=lambda x: {
            'auto': '🔄 ' + ('Automatyczny (jak CV)' if ui_language == 'pl' else 'Auto (same as CV)'),
            'pl': '🇵🇱 Polski',
            'en': '🇬🇧 English'
        }[x],
        index=0
    )
    
    st.markdown("---")
    
    # ============= ADD TEMPLATE SELECTOR HERE =============
    # Template selection - NOWE!
    template_type = st.selectbox(
        "📋 " + ("Szablon raportu" if ui_language == 'pl' else "Report Template"),
        options=['full', 'short', 'anonymous', 'extended', 'one_to_one'],
        format_func=lambda x: {
            'full': '📄 ' + ('Pełny (z danymi)' if ui_language == 'pl' else 'Full (with data)'),
            'short': '📝 ' + ('Skrócony' if ui_language == 'pl' else 'Short'),
            'anonymous': '🔒 ' + ('Anonimowy (bez danych)' if ui_language == 'pl' else 'Anonymous (no data)'),
            'extended': '📚 ' + ('Rozszerzony (szczegółowy)' if ui_language == 'pl' else 'Extended (detailed)'),
            'one_to_one': '1️⃣ ' + ('1:1 z CV (bez rekomendacji)' if ui_language == 'pl' else '1:1 from CV (no recommendation)')
        }[x],
        index=0,
        help="Wybierz typ szablonu raportu" if ui_language == 'pl' else "Select report template type"
    )

    
    # Template description
    template_descriptions = {
        'pl': {
            'full': '✓ Wszystkie dane kontaktowe\n✓ Pełne doświadczenie\n✓ Szczegółowa analiza',
            'short': '✓ Kluczowe informacje\n✓ Top 3 doświadczenia\n✓ 5 głównych umiejętności',
            'anonymous': '✓ Bez danych osobowych\n✓ Ukryte firmy/uczelnie\n✓ Tylko kompetencje',
            'extended': '✓ Pełne CV + analiza\n✓ Pytania rekrutacyjne\n✓ Obszary rozwoju',
            'one_to_one': '✓ Struktura z CV\n✓ Zadania 1:1 z analizy\n✓ Bez rekomendacji i podsumowań'
        },
        'en': {
            'full': '✓ All contact details\n✓ Full experience\n✓ Detailed analysis',
            'short': '✓ Key information\n✓ Top 3 experiences\n✓ 5 main skills',
            'anonymous': '✓ No personal data\n✓ Hidden companies/universities\n✓ Competencies only',
            'extended': '✓ Full CV + analysis\n✓ Interview questions\n✓ Development areas',
            'one_to_one': '✓ Structure from CV\n✓ Tasks 1:1 from analysis\n✓ No recommendations/summary'
        }
    }

    
    st.info(template_descriptions[ui_language][template_type])
    # ============= END OF TEMPLATE SELECTOR =============
    
    st.markdown("---")
    st.info(t['tip'])

# Header
st.markdown(f'<h1 class="main-header">{t["title"]}</h1>', unsafe_allow_html=True)
st.markdown("---")

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown(f'<div class="section-header">{t["upload_cv"]}</div>', unsafe_allow_html=True)
    
    # File uploader
    uploaded_file = st.file_uploader(
        t['choose_file'],
        type=['pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png'],
        help=t['supported_formats']
    )
    
    if uploaded_file is not None:
        # RESETUJ SESSION STATE DLA NOWEGO PLIKU!
        current_file_name = st.session_state.get('current_file_name', None)
        
        if current_file_name != uploaded_file.name:
            # Nowy plik - resetuj wszystko
            st.session_state['analysis_result'] = None
            st.session_state['cv_text'] = None
            st.session_state['current_file_name'] = uploaded_file.name
            st.rerun()  # Wymusza odświeżenie UI
        
        st.success(f"✅ {t['file_uploaded']}: {uploaded_file.name}")
        file_details = {
            t['filename']: uploaded_file.name,
            t['filetype']: uploaded_file.type,
            t['filesize']: f"{uploaded_file.size / 1024:.2f} KB"
        }
        st.json(file_details)

with col2:
    st.markdown(f'<div class="section-header">{t["client_req"]}</div>', unsafe_allow_html=True)
    
    # Client requirements input
    client_requirements = st.text_area(
        t['enter_req'],
        value="",                      # brak startowego tekstu
        placeholder=t['default_req'],  # szary tekst‑podpowiedź
        help=t['req_help'],
        height=220,
    )

# Custom Prompt (Optional)
st.markdown(f'<div class="section-header">{t["custom_prompt"]}</div>', unsafe_allow_html=True)

with st.expander(t['advanced']):
    use_custom_prompt = st.checkbox(t['use_custom'])
    
    if use_custom_prompt:
        custom_prompt = st.text_area(
            t['custom_template'],
            value="Analyze the following CV and extract key information.\n\nCV:\n{cv_text}\n\nRequirements:\n{client_requirements}\n\nProvide analysis in JSON format.",
            height=150,
            help=t['prompt_help']
        )
    else:
        custom_prompt = ""

# Analyze Button
st.markdown("---")
col_analyze, col_download = st.columns([1, 1])

with col_analyze:
    if st.button(t['analyze_btn'], type="primary", use_container_width=True):
        if uploaded_file is not None and client_requirements:
            with st.spinner(t['analyzing']):
                try:
                    # Initialize analyzer
                    analyzer = CVAnalyzer(model_name=model_name)
                    
                    # Extract text from CV
                    cv_text = analyzer.load_cv(uploaded_file)
                    
                    if "Error" in cv_text or "Unsupported" in cv_text:
                        st.error(f"{t['error_extract']} {cv_text}")
                    else:
                        st.session_state.cv_text = cv_text
                        st.success(f"{t['text_extracted']} {len(cv_text)} {t['characters']}")
                        
                        # Map output language codes - DODAJ TO!
                        lang_map = {'auto': 'auto', 'pl': 'polish', 'en': 'english'}
                        mapped_output_lang = lang_map.get(output_language, 'auto')
                        
                        # Analyze CV
                        analysis = analyzer.analyze_cv_for_template(
                            cv_text, 
                            client_requirements,
                            custom_prompt if use_custom_prompt else "",
                            output_language=mapped_output_lang  # <-- POPRAWIONE
                        )
                        
                        if "error" in analysis or "parsing_error" in analysis:
                            st.error(f"{t['analysis_failed']} {analysis.get('error', analysis.get('parsing_error'))}")
                            if 'raw_analysis' in analysis:
                                with st.expander(t['view_raw']):
                                    st.text(analysis['raw_analysis'][:1000])
                        else:
                            st.session_state.analysis_result = analysis
                            st.success(t['analysis_complete'])
                
                except Exception as e:
                    st.error(f"{t['error']} {str(e)}")
        else:
            st.warning(t['upload_warning'])

# Display Results
if st.session_state.analysis_result is not None:
    st.markdown("---")
    st.markdown(f'<div class="section-header">{t["results_header"]}</div>', unsafe_allow_html=True)
    
    analysis = st.session_state.analysis_result
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs([t['tab_structured'], t['tab_json'], t['tab_text']])
    
    with tab1:
        # Basic Info
        if "detected_language" in analysis and "output_language" in analysis:
            cv_lang = analysis["detected_language"]
            out_lang = analysis.get("output_language", cv_lang)
            
            if cv_lang != out_lang:
                lang_names = {
                    'polish': {'pl': '🇵🇱 Polski', 'en': '🇵🇱 Polish'},
                    'english': {'pl': '🇬🇧 Angielski', 'en': '🇬🇧 English'}
                }
                cv_lang_display = lang_names.get(cv_lang, {}).get(ui_language, cv_lang)
                out_lang_display = lang_names.get(out_lang, {}).get(ui_language, out_lang)
                
                st.info(f"🔄 CV: {cv_lang_display} → " + 
                       ("Raport" if ui_language == 'pl' else "Report") + 
                       f": {out_lang_display} (" + 
                       ("z tłumaczeniem" if ui_language == 'pl' else "translated") + ")")

        if 'podstawowe_dane' in analysis or 'basic_data' in analysis:
            st.subheader(t['basicinfo'])
            dane = analysis.get('podstawowe_dane') or analysis.get('basic_data')
            
            col1, col2, col3 = st.columns(3)
            col1.metric(t['name'], dane.get('imie_nazwisko') or dane.get('full_name') or dane.get('name') or "NA")
            col2.metric(t['email'], dane.get('email') or "NA")
            col3.metric(t['phone'], dane.get('telefon') or dane.get('phone') or "NA")
        
        # Location & Availability
        if 'lokalizacja_i_dostepnosc' in analysis or 'location_and_availability' in analysis:
            st.subheader(t['locationavail'])
            lok = analysis.get('lokalizacja_i_dostepnosc') or analysis.get('location_and_availability')
            
            col1, col2, col3 = st.columns(3)
            col1.metric(t['location'], lok.get('lokalizacja') or lok.get('location') or "NA")
            col2.metric(t['remotework'], lok.get('preferencja_pracy_zdalnej') or lok.get('remote_work_preference') or "NA")
            col3.metric(t['availability'], lok.get('dostepnosc') or lok.get('availability') or "NA")
        
        # Candidate Summary
        if 'krotki_opis_kandydata' in analysis or 'profile_summary' in analysis:
            st.subheader(t['summary'])
            summary = analysis.get('krotki_opis_kandydata') or analysis.get('profile_summary') or analysis.get('podsumowanie_profilu')
            st.info(summary)
        
        # Tech Stack
        if 'stack_technologiczny' in analysis or 'skills' in analysis or 'umiejetnosci' in analysis:
            st.subheader(t['techstack'])
            stack = analysis.get('stack_technologiczny') or analysis.get('skills') or analysis.get('umiejetnosci')
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"{t['languagesprog']}: ", ", ".join(stack.get('jezyki_programowania') or stack.get('programming_scripting') or []))
                st.write(f"{t['frameworks']}: ", ", ".join(stack.get('frameworki') or stack.get('frameworks_libraries') or []))
            with col2:
                st.write(f"{t['databases']}: ", ", ".join(stack.get('bazy_danych') or stack.get('databases_messaging') or []))
                st.write(f"{t['tools']}: ", ", ".join(stack.get('narzedzia') or stack.get('infrastructure_devops') or []))
        
        # Fit Assessment
        if 'dopasowanie_do_wymagan' in analysis or 'matching_to_requirements' in analysis:
            st.subheader(t['fit_assessment'])
            dop = analysis.get('dopasowanie_do_wymagan') or analysis.get('matching_to_requirements', {})
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(t['match_level'])
                match_level = dop.get('poziom_dopasowania') or dop.get('match_level', 'N/A')
                
                # Mapowanie dla angielskiej wersji
                if ui_language == 'en' and match_level != 'N/A':
                    level_mapping = {
                        'niski': 'Low',
                        'średni': 'Medium',
                        'wysoki': 'High',
                        'bardzo wysoki': 'Very High'
                    }
                    match_level = level_mapping.get(match_level.lower(), match_level)
                
                if match_level.lower() in ['wysoki', 'high', 'bardzo wysoki', 'very high']:
                    color = "#d4edda"
                    text_color = "#155724"
                elif match_level.lower() in ['średni', 'medium']:
                    color = "#fff3cd"
                    text_color = "#856404"
                else:
                    color = "#f8d7da"
                    text_color = "#721c24"
                
                st.markdown(f"""
                    <div style='background-color: {color}; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid {text_color}'>
                        <h2 style='color: {text_color}; margin: 0'>{match_level.upper()}</h2>
                    </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(t['recommendation'])
                recommendation = dop.get('rekomendacja') or dop.get('recommendation', 'N/A')
                
                # Mapowanie dla angielskiej wersji
                if ui_language == 'en' and recommendation != 'N/A':
                    rec_mapping = {
                        'tak': 'Yes',
                        'nie': 'No',
                        'warunkowa': 'Conditional',
                        'no - does not meet requirements': 'No - Does Not Meet Requirements'
                    }
                    recommendation = rec_mapping.get(recommendation.lower(), recommendation)
                
                if recommendation.upper() in ['TAK', 'YES']:
                    color = "#d4edda"
                    text_color = "#155724"
                else:
                    color = "#f8d7da"
                    text_color = "#721c24"
                
                st.markdown(f"""
                    <div style='background-color: {color}; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid {text_color}'>
                        <h2 style='color: {text_color}; margin: 0'>{recommendation.upper()}</h2>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Uzasadnienie w osobnej sekcji z możliwością przewijania
            if dop.get('uzasadnienie'):
                st.markdown("#### " + t['justification'].replace('**', '').replace(':', ''))
                # Używamy expander dla długich tekstów
                with st.expander("📄 " + ("Kliknij aby rozwinąć" if ui_language == 'pl' else "Click to expand"), expanded=True):
                    st.write(dop.get('uzasadnienie', 'N/A'))
            
            # Kluczowe mocne strony
            if 'mocne_strony' in dop and dop['mocne_strony']:
                st.markdown("#### " + t['key_strengths'].replace('**', '').replace(':', ''))
                
                # Wyświetl w dwóch kolumnach dla lepszego layoutu
                strengths = dop['mocne_strony']
                mid = len(strengths) // 2 + len(strengths) % 2
                
                col1, col2 = st.columns(2)
                with col1:
                    for i, strength in enumerate(strengths[:mid], 1):
                        st.markdown(f"✅ **{i}.** {strength}")
                with col2:
                    for i, strength in enumerate(strengths[mid:], mid + 1):
                        st.markdown(f"✅ **{i}.** {strength}")
    
    with tab2:
        st.json(analysis)
    
    with tab3:
        if st.session_state.cv_text:
            st.text_area(t['extracted_text'], st.session_state.cv_text, height=400)

# Download Section
with col_download:
    if st.session_state.analysis_result is not None:
        st.markdown("### 📥 Pobierz raport")
        
        # DODAJ EDYTOWALNĄ NAZWĘ PLIKU
        default_name = uploaded_file.name.rsplit('.', 1)[0] if uploaded_file else "cv_analysis"
        
        custom_filename = st.text_input(
            "Nazwa pliku raportu" if ui_language == 'pl' else "Report filename",
            value=f"{default_name}_{template_type}",
            help="Bez rozszerzenia (.pdf/.docx)" if ui_language == 'pl' else "Without extension (.pdf/.docx)"
        )
        
        # Usuń nielegalne znaki z nazwy pliku
        import re
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', custom_filename)
        
        analyzer = CVAnalyzer(model_name=model_name)
        
        if output_format == "PDF":
            pdf_language = 'pl' if 'Polski' in st.session_state.get('language_choice', 'English') else 'en'
            
            pdf_buffer = analyzer.generate_pdf_output(
                st.session_state.analysis_result,
                template_type=template_type,
                language=pdf_language,
                client_requirements=client_requirements
            )
            
            st.download_button(
                label=f"📄 {t['download_pdf']}",
                data=pdf_buffer,
                file_name=f"{safe_filename}.pdf",  # ← UŻYJ CUSTOM NAZWY
                mime="application/pdf",
                use_container_width=True
            )
            
        elif output_format == "DOCX":
            lang_map = {'auto': 'auto', 'pl': 'polish', 'en': 'english'}
            mapped_output_lang = lang_map.get(output_language, 'auto')
            
            docx_buffer = analyzer.generate_docx_output(
                st.session_state.analysis_result,
                template_type=template_type,
                language=mapped_output_lang,
                client_requirements=client_requirements
            )
            
            if docx_buffer and isinstance(docx_buffer, BytesIO):
                st.download_button(
                    label=f"📄 {t['download_docx']}",
                    data=docx_buffer.getvalue(),
                    file_name=f"{safe_filename}.docx",  # ← UŻYJ CUSTOM NAZWY
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
            else:
                st.error("❌ DOCX generation failed. Check backend logs.")
        
                      
if st.session_state.analysis_result is not None:
    st.markdown("---")
    st.markdown(f'<div class="section-header">{t["aitab"]}</div>', unsafe_allow_html=True)
    
    # AI Assistant translations
    ai_t = {
        'spell_check_tab': 'Korekta tekstu' if ui_language == 'pl' else 'Text Correction',
        'text_gen_tab': 'Generowanie treści' if ui_language == 'pl' else 'Content Generation',
        'paste_text': 'Wklej tekst do sprawdzenia:' if ui_language == 'pl' else 'Paste text to check:',
        'spell_check': 'Sprawdź literówki' if ui_language == 'pl' else 'Check spelling',
        'checking': 'Sprawdzam...' if ui_language == 'pl' else 'Checking...',
        'corrected': 'Poprawiony tekst:' if ui_language == 'pl' else 'Corrected text:',
        'select_data': 'Wybierz dane:' if ui_language == 'pl' else 'Select data:',
        'instruction': 'Instrukcja:' if ui_language == 'pl' else 'Instruction:',
        'generate': 'Generuj' if ui_language == 'pl' else 'Generate',
        'generating': 'Generuję...' if ui_language == 'pl' else 'Generating...',
        'result': 'Wynik:' if ui_language == 'pl' else 'Result:'
    }
    
    ai_tab1, ai_tab2 = st.tabs([f"📝 {ai_t['spell_check_tab']}", f"✨ {ai_t['text_gen_tab']}"])
    
    # Tab 1: Spell Check
    with ai_tab1:
        st.write(ai_t['paste_text'])
        text_to_check = st.text_area(
            "text_check",
            value="",
            height=150,
            key="spell_input",
            label_visibility="collapsed"
        )
        
        if st.button(f"🔍 {ai_t['spell_check']}", type="primary"):
            if text_to_check:
                with st.spinner(ai_t['checking']):
                    analyzer = CVAnalyzer(model_name=model_name)
                    corrected = analyzer.spell_check_cv(text_to_check)
                    st.session_state['corrected_text'] = corrected
        
        if 'corrected_text' in st.session_state:
            st.success(ai_t['corrected'])
            st.text_area("corrected", value=st.session_state['corrected_text'], height=150, key="spell_output", label_visibility="collapsed")
    
    # Tab 2: Text Generation
    with ai_tab2:
        analysis = st.session_state.analysis_result
        st.write(ai_t['select_data'])

        col1, col2 = st.columns(2)
        with col1:
            inc_tech = st.checkbox(t['ait_techstack'], value=True)
            inc_exp = st.checkbox(t['ait_experience'], value=True)
        with col2:
            inc_skills = st.checkbox(t['ait_skills'], value=True)
            inc_summary = st.checkbox(t['ait_description'], value=True)

        context_data = {}
        
        # Fix 1: Use correct English keys from your analysis
        if inc_tech and 'tech_stack_summary' in analysis:
            tech = analysis['tech_stack_summary']
            primary_techs = tech.get('primary_technologies', [])
            context_data['TechStack'] = ', '.join(primary_techs) if primary_techs else ''
        
        if inc_exp and 'work_experience' in analysis:
            jobs = analysis['work_experience']
            exp_summary = []
            for job in jobs[:3]:  # Top 3 positions
                company = job.get('company', '')
                position = job.get('position', '')
                if company and position:
                    exp_summary.append(f"{position} at {company}")
            context_data['Experience'] = '; '.join(exp_summary) if exp_summary else ''
        
        if inc_skills and 'skills' in analysis:
            skills = analysis['skills']
            all_skills = []
            # Collect all skills from all categories
            for category, skill_list in skills.items():
                if isinstance(skill_list, list):
                    all_skills.extend(skill_list[:5])  # Top 5 from each category
            context_data['Skills'] = ', '.join(all_skills[:15]) if all_skills else ''  # Max 15 total
        
        if inc_summary and 'profile_summary' in analysis:
            context_data['ProfileSummary'] = analysis['profile_summary']

        # Also add matching info if available
        if 'matching_to_requirements' in analysis:
            match = analysis['matching_to_requirements']
            if 'strengths' in match:
                context_data['Strengths'] = '; '.join(match['strengths'][:3])

        st.write(ai_t['instruction'])

        # Initialize session state for instruction
        if "ai_instr" not in st.session_state:
            st.session_state["ai_instr"] = ""

        # Quick action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(t['ait_btn_tasks'], use_container_width=True):
                st.session_state["ai_instr"] = t['ait_prompt_tasks']
        with col2:
            if st.button(t['ait_btn_profile'], use_container_width=True):
                st.session_state["ai_instr"] = t['ait_prompt_profile']
        with col3:
            if st.button(t['ait_btn_justify'], use_container_width=True):
                st.session_state["ai_instr"] = t['ait_prompt_justify']

        # Text area for instruction
        instruction = st.text_area(
            "instr", 
            placeholder=t['ait_placeholder'],
            height=80, 
            key="ai_instr", 
            label_visibility="collapsed"
        )

        # Generate button
        if st.button(f"✨ {ai_t['generate']}", type="primary"):
            if st.session_state["ai_instr"].strip() and context_data:
                with st.spinner(ai_t['generating']):
                    analyzer = CVAnalyzer(model_name=model_name)
                    generated = analyzer.ai_text_assistant(
                        st.session_state["ai_instr"], 
                        context_data
                    )
                    st.session_state['generated'] = generated
            else:
                st.warning(t['ait_warning'])

        # Display generated content
        if 'generated' in st.session_state:
            st.success(ai_t['result'])
            st.info(st.session_state['generated'])


# Footer
st.markdown("---")
st.markdown(t['footer'])