import streamlit as st
from cv_analyzer_backend import CVAnalyzer
import json

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
        'footer': 'Stworzone z ❤️ przy użyciu Streamlit & Ollama | 2025'
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
        'footer': 'Made with ❤️ using Streamlit & Ollama | 2025'
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
    model_name = st.selectbox(
        t['select_model'],
        ["qwen2.5:14b", "llama3.1:8b", "deepseek-r1:8b", "gemma2:9b", "mistral:7b"],
        index=0
    )
    
    # Output format (ALREADY EXISTS)
    output_format = st.radio(
        t['output_format'],
        ["PDF", "DOCX", "JSON"],
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
        options=['full', 'short', 'anonymous', 'extended'],
        format_func=lambda x: {
            'full': '📄 ' + ('Pełny (z danymi)' if ui_language == 'pl' else 'Full (with data)'),
            'short': '📝 ' + ('Skrócony' if ui_language == 'pl' else 'Short'),
            'anonymous': '🔒 ' + ('Anonimowy (bez danych)' if ui_language == 'pl' else 'Anonymous (no data)'),
            'extended': '📚 ' + ('Rozszerzony (szczegółowy)' if ui_language == 'pl' else 'Extended (detailed)')
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
            'extended': '✓ Pełne CV + analiza\n✓ Pytania rekrutacyjne\n✓ Obszary rozwoju'
        },
        'en': {
            'full': '✓ All contact details\n✓ Full experience\n✓ Detailed analysis',
            'short': '✓ Key information\n✓ Top 3 experiences\n✓ 5 main skills',
            'anonymous': '✓ No personal data\n✓ Hidden companies/universities\n✓ Competencies only',
            'extended': '✓ Full CV + analysis\n✓ Interview questions\n✓ Development areas'
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
        st.success(f"{t['file_uploaded']} {uploaded_file.name}")
        
        # File info
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
        value=t['default_req'],
        height=200,
        help=t['req_help']
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

        if "podstawowe_dane" in analysis:
            st.subheader(t['basic_info'])
            dane = analysis["podstawowe_dane"]
            col1, col2, col3 = st.columns(3)
            col1.metric(t['name'], dane.get('imie_nazwisko', 'N/A'))
            col2.metric(t['email'], dane.get('email', 'N/A'))
            col3.metric(t['phone'], dane.get('telefon', 'N/A'))
        
        # Location & Availability
        if "lokalizacja_i_dostepnosc" in analysis:
            st.subheader(t['location_avail'])
            lok = analysis["lokalizacja_i_dostepnosc"]
            col1, col2, col3 = st.columns(3)
            col1.metric(t['location'], lok.get('lokalizacja', 'N/A'))
            col2.metric(t['remote_work'], lok.get('preferencja_pracy_zdalnej', 'N/A'))
            col3.metric(t['availability'], lok.get('dostepnosc', 'N/A'))
        
        # Candidate Summary
        if "krotki_opis_kandydata" in analysis:
            st.subheader(t['summary'])
            st.info(analysis["krotki_opis_kandydata"])
        
        # Tech Stack
        if "stack_technologiczny" in analysis:
            st.subheader(t['tech_stack'])
            stack = analysis["stack_technologiczny"]
            col1, col2 = st.columns(2)
            with col1:
                st.write(t['languages_prog'], ", ".join(stack.get('jezyki_programowania', [])))
                st.write(t['frameworks'], ", ".join(stack.get('frameworki', [])))
            with col2:
                st.write(t['databases'], ", ".join(stack.get('bazy_danych', [])))
                st.write(t['tools'], ", ".join(stack.get('narzedzia', [])))
        
        # Fit Assessment
        if "dopasowanie_do_wymagan" in analysis:
            st.subheader(t['fit_assessment'])
            dop = analysis["dopasowanie_do_wymagan"]
            
            # Match Level and Recommendation w osobnych kolumnach z lepszym formatowaniem
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### " + t['match_level'])
                match_level = dop.get('poziom_dopasowania', 'N/A')
                # Kolorowe tło w zależności od poziomu
                if match_level.lower() in ['wysoki', 'high']:
                    color = '#d4edda'
                    text_color = '#155724'
                elif match_level.lower() in ['sredni', 'medium']:
                    color = '#fff3cd'
                    text_color = '#856404'
                else:
                    color = '#f8d7da'
                    text_color = '#721c24'
                
                st.markdown(f"""
                <div style='background-color: {color}; 
                            padding: 20px; 
                            border-radius: 10px; 
                            text-align: center;
                            border: 2px solid {text_color};'>
                    <h2 style='color: {text_color}; margin: 0;'>{match_level.upper()}</h2>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("#### " + t['recommendation'])
                recommendation = dop.get('rekomendacja', 'N/A')
                # Kolorowe tło w zależności od rekomendacji
                if recommendation.upper() in ['TAK', 'YES']:
                    color = '#d4edda'
                    text_color = '#155724'
                else:
                    color = '#f8d7da'
                    text_color = '#721c24'
                
                st.markdown(f"""
                <div style='background-color: {color}; 
                            padding: 20px; 
                            border-radius: 10px; 
                            text-align: center;
                            border: 2px solid {text_color};'>
                    <h2 style='color: {text_color}; margin: 0;'>{recommendation.upper()}</h2>
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
        analyzer = CVAnalyzer(model_name=model_name)
        
        # Add template type caption
        st.caption(f"Szablon: {template_type.upper()}")
        
        if output_format == "PDF":
            pdf_buffer = analyzer.generate_pdf_output(
                st.session_state.analysis_result,
                template_type=template_type  # ← MAKE SURE THIS IS HERE
            )
            st.download_button(
                label=t['download_pdf'],
                data=pdf_buffer,
                file_name=f"cv_analysis_{template_type}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        elif output_format == "DOCX":
            docx_buffer = analyzer.generate_docx_output(
                st.session_state.analysis_result,
                template_type=template_type  # ← MAKE SURE THIS IS HERE
            )
            st.download_button(
                label=t['download_docx'],
                data=docx_buffer,
                file_name=f"cv_analysis_{template_type}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        else:  # JSON
            # Apply filter for JSON too
            filtered_json = analyzer.apply_template_filters(
                st.session_state.analysis_result,
                template_type
            )
            json_str = json.dumps(filtered_json, ensure_ascii=False, indent=2)
            st.download_button(
                label=t['download_json'],
                data=json_str,
                file_name=f"cv_analysis_{template_type}.json",
                mime="application/json",
                use_container_width=True
            )
if st.session_state.analysis_result is not None:
    st.markdown("---")
    st.markdown('<div class="section-header">🤖 AI Assistant / Asystent AI</div>', unsafe_allow_html=True)
    
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
            inc_tech = st.checkbox("Stack Technologiczny", value=True)
            inc_exp = st.checkbox("Doświadczenie", value=True)
        with col2:
            inc_skills = st.checkbox("Umiejętności", value=True)
            inc_summary = st.checkbox("Opis", value=True)
        
        context_data = {}
        if inc_tech and "stack_technologiczny" in analysis:
            stack = analysis["stack_technologiczny"]
            context_data["Tech"] = ", ".join(stack.get("jezyki_programowania", []) + stack.get("frameworki", []))
        if inc_exp and "doswiadczenie_zawodowe" in analysis:
            context_data["Experience"] = f"{len(analysis['doswiadczenie_zawodowe'])} positions"
        if inc_skills and "dopasowanie_do_wymagan" in analysis:
            if "mocne_strony" in analysis["dopasowanie_do_wymagan"]:
                context_data["Strengths"] = analysis["dopasowanie_do_wymagan"]["mocne_strony"][:3]
        if inc_summary and "krotki_opis_kandydata" in analysis:
            context_data["Summary"] = analysis["krotki_opis_kandydata"]
        
        st.write(ai_t['instruction'])
        instruction = st.text_area("instr", placeholder="np. 'Opisz zadania na podstawie stacku'", height=80, key="ai_instr", label_visibility="collapsed")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📝 Opis zadań", use_container_width=True):
                instruction = "Na podstawie stacku opisz szczegółowe zadania programisty"
        with col2:
            if st.button("💼 Profil", use_container_width=True):
                instruction = "Wygeneruj zwięzły opis profilu kandydata (3-4 zdania)"
        with col3:
            if st.button("🎯 Uzasadnienie", use_container_width=True):
                instruction = "Napisz dlaczego ten kandydat jest idealny na stanowisko"
        
        if st.button(f"✨ {ai_t['generate']}", type="primary"):
            if instruction and context_data:
                with st.spinner(ai_t['generating']):
                    analyzer = CVAnalyzer(model_name=model_name)
                    generated = analyzer.ai_text_assistant(instruction, context_data)
                    st.session_state['generated'] = generated
        
        if 'generated' in st.session_state:
            st.success(ai_t['result'])
            st.info(st.session_state['generated'])
# Footer
st.markdown("---")
st.markdown(t['footer'])