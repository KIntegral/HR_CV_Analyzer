import pymupdf
from PIL import Image
import pytesseract
import ollama
import json
import os

from docx.oxml import parse_xml
from fpdf import FPDF

from PIL import Image
import numpy as np
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from docx.shared import Pt, RGBColor, Inches
from docx.enum.section import WD_SECTION

from reportlab.lib.enums import TA_LEFT
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os
# Dla Windows odkomentuj:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

try:
    # Próba użycia systemowych fontów
    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))
except:
    # Jeśli nie ma DejaVu, użyj domyślnych z ReportLab
    from reportlab.lib.fonts import addMapping
    # ReportLab ma wbudowane fonty z podstawowym wsparciem UTF-8

class CVAnalyzer:
    def __init__(self, model_name="qwen2.5:14b"):
        self.model_name = model_name
        
    def extract_text_from_pdf(self, pdf_file):
        """Extract text from PDF file or BytesIO object"""
        try:
            doc = pymupdf.open(stream=pdf_file.read() if hasattr(pdf_file, 'read') else pdf_file, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            return "Error reading PDF: " + str(e)
    
    def extract_text_from_docx(self, docx_file):
        """Extract text from DOCX file"""
        try:
            doc = Document(docx_file)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        except Exception as e:
            return "Error reading DOCX: " + str(e)
    
    def extract_text_from_image(self, image_file):
        """Extract text from image using OCR"""
        try:
            image = Image.open(image_file)
            image = image.convert('L')
            text = pytesseract.image_to_string(image, lang='pol+eng')
            return text
        except Exception as e:
            return "Error reading image: " + str(e)
    
    def load_cv(self, uploaded_file):
        """Load CV from uploaded file"""
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension == 'pdf':
            return self.extract_text_from_pdf(uploaded_file)
        elif file_extension in ['docx', 'doc']:
            return self.extract_text_from_docx(uploaded_file)
        elif file_extension in ['jpg', 'jpeg', 'png']:
            return self.extract_text_from_image(uploaded_file)
        else:
            return "Unsupported file format. Use PDF, DOCX, or JPG/PNG."
    
    def detect_language(self, text):
        """Simple language detection"""
        polish_keywords = ['doswiadczenie', 'umiejetnosci', 'edukacja', 'certyfikat', 'stanowisko']
        english_keywords = ['experience', 'skills', 'education', 'certificate', 'position']
        
        text_lower = text.lower()
        polish_count = sum(1 for word in polish_keywords if word in text_lower)
        english_count = sum(1 for word in english_keywords if word in text_lower)
        
        return 'polish' if polish_count > english_count else 'english'
    
    def analyze_cv_for_template(self, cv_text, client_requirements, custom_prompt="", output_language='auto'):
        """
        Analyze CV and generate structured template
        output_language: 'auto', 'pl', or 'en'
        """
        cv_language = self.detect_language(cv_text)
        
        # Determine final output language
        if output_language == 'auto':
            final_language = cv_language
        else:
            final_language = output_language
        
        if custom_prompt:
            prompt = custom_prompt.replace("{cv_text}", cv_text).replace("{client_requirements}", client_requirements)
        else:
            # Check if translation is needed
            needs_translation = (cv_language != final_language)
            
            if final_language == 'polish':
                prompt = self._create_polish_prompt(cv_text, client_requirements, needs_translation, cv_language)
            else:
                prompt = self._create_english_prompt(cv_text, client_requirements, needs_translation, cv_language)

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': prompt}],
                options={
                    'temperature': 0.2,
                    'top_p': 0.9,
                    'seed': 42,
                    'num_predict': 4000,
                    'repeat_penalty': 1.1
                }
            )
            
            analysis = response['message']['content']
            
            try:
                start_pos = analysis.find('{')
                end_pos = analysis.rfind('}')
                
                if start_pos != -1 and end_pos != -1:
                    analysis = analysis[start_pos:end_pos+1]
                
                # POPRAWKA: używaj parsed_analysis zamiast parsedfiltered
                parsed_analysis = json.loads(analysis)
                parsed_analysis['detected_language'] = cv_language
                parsed_analysis['output_language'] = final_language
                return parsed_analysis
                
            except json.JSONDecodeError as je:
                return {"raw_analysis": analysis, "parsing_error": "Failed to parse JSON: " + str(je)}
                
        except Exception as e:
            return {"error": "Error during LLM analysis: " + str(e)}
    
    def ai_text_assistant(self, instruction, context_data, model_name=None):
        """
        AI Assistant for text generation and transformation
        instruction: User command (e.g., "Fix typos", "Generate job description based on tech stack")
        context_data: Dictionary with relevant data from CV
        """
        if model_name is None:
            model_name = self.model_name
        
        # Build context from data
        context = "CONTEXT DATA:\n"
        for key, value in context_data.items():
            if isinstance(value, list):
                context += f"{key}: {', '.join(map(str, value))}\n"
            else:
                context += f"{key}: {value}\n"
        
        prompt = f"""You are an AI writing assistant for HR professionals.

    {context}

    USER INSTRUCTION: {instruction}

    Please execute the instruction based on the context provided above.
    Respond in the same language as the instruction.
    Be professional, clear, and concise.
    If correcting text, maintain the original structure but fix errors.
    If generating text, make it relevant to HR and recruitment context.

    YOUR RESPONSE:"""

        try:
            response = ollama.chat(
                model=model_name,
                messages=[{'role': 'user', 'content': prompt}],
                options={
                    'temperature': 0.7,  # Higher for creative tasks
                    'top_p': 0.9,
                    'num_predict': 1000
                }
            )
            
            return response['message']['content']
        except Exception as e:
            return f"Error: {str(e)}"

    def apply_template_filters(self, analysis, template_type='full'):
        """
        Apply template filters to analysis data
        template_type: 'full', 'short', 'anonymous', 'extended'
        """
        import copy
        filtered = copy.deepcopy(analysis)
        
        if template_type == 'short':
            # Skrócona wersja - tylko najważniejsze informacje
            if 'doswiadczenie_zawodowe' in filtered and len(filtered['doswiadczenie_zawodowe']) > 3:
                filtered['doswiadczenie_zawodowe'] = filtered['doswiadczenie_zawodowe'][:3]
            
            if 'dopasowanie_do_wymagan' in filtered:
                if 'mocne_strony' in filtered['dopasowanie_do_wymagan'] and len(filtered['dopasowanie_do_wymagan']['mocne_strony']) > 5:
                    filtered['dopasowanie_do_wymagan']['mocne_strony'] = filtered['dopasowanie_do_wymagan']['mocne_strony'][:5]
                
                # Usuń mapowanie wymagań w wersji skróconej
                if 'mapowanie_wymagan' in filtered['dopasowanie_do_wymagan']:
                    del filtered['dopasowanie_do_wymagan']['mapowanie_wymagan']
                if 'analiza_jakosciowa' in filtered['dopasowanie_do_wymagan']:
                    del filtered['dopasowanie_do_wymagan']['analiza_jakosciowa']
            
            # Usuń certyfikaty jeśli jest ich dużo
            if 'certyfikaty' in filtered and len(filtered.get('certyfikaty', [])) > 3:
                filtered['certyfikaty'] = filtered['certyfikaty'][:3]
        
        elif template_type == 'anonymous':
            # Anonimowa wersja - bez danych osobowych
            if 'podstawowe_dane' in filtered:
                filtered['podstawowe_dane'] = {
                    'imie_nazwisko': 'Kandydat [anonimowy]',
                    'email': '[ukryty]',
                    'telefon': '[ukryty]'
                }
            
            # Ukryj nazwy firm
            if 'doswiadczenie_zawodowe' in filtered:
                for idx, exp in enumerate(filtered['doswiadczenie_zawodowe']):
                    exp['nazwa_firmy'] = f'Firma #{idx+1} [anonimowa]'
            
            # Ukryj nazwy uczelni
            if 'edukacja' in filtered:
                for idx, edu in enumerate(filtered['edukacja']):
                    edu['uczelnia'] = f'Uczelnia #{idx+1} [anonimowa]'
            
            # Ogólna lokalizacja
            if 'lokalizacja_i_dostepnosc' in filtered:
                loc = filtered['lokalizacja_i_dostepnosc'].get('lokalizacja', '')
                if loc and loc != 'nieokreslona w CV':
                    # Zostaw tylko kraj lub region
                    parts = loc.split(',')
                    if len(parts) > 1:
                        filtered['lokalizacja_i_dostepnosc']['lokalizacja'] = parts[-1].strip()
        
        elif template_type == 'extended':
            # Rozszerzona wersja - dodaj dodatkowe sekcje jeśli są
            # W tej wersji zachowujemy wszystko + dodajemy rozszerzoną analizę
            if 'dopasowanie_do_wymagan' in filtered:
                # Dodaj placeholder dla rozszerzonych rekomendacji
                if 'extended_recommendations' not in filtered['dopasowanie_do_wymagan']:
                    filtered['dopasowanie_do_wymagan']['extended_recommendations'] = {
                        'interview_questions': [
                            'Pytanie 1: Opisz największy projekt w którym brałeś udział',
                            'Pytanie 2: Jak radzisz sobie z trudnymi sytuacjami w zespole?',
                            'Pytanie 3: Jakie są Twoje plany rozwoju na najbliższe 2 lata?'
                        ],
                        'development_areas': [
                            'Obszary do rozwoju zostaną uzupełnione po rozmowie'
                        ],
                        'salary_expectation': 'Do ustalenia podczas rozmowy'
                    }
        
        # 'full' - zwraca wszystko bez zmian
        filtered['key_highlights'] = self.extract_key_highlights(filtered)
        return filtered

    def spell_check_cv(self, cv_text, language='auto'):
        """
        Check and correct spelling/grammar in CV
        """
        if language == 'auto':
            detected_lang = self.detect_language(cv_text)
            lang_name = 'Polish' if detected_lang == 'polish' else 'English'
        else:
            lang_name = language
        
        prompt = f"""You are a professional proofreader specializing in CVs/resumes.

    ORIGINAL TEXT:
    {cv_text}

    TASK: Review the text above and:
    1. Fix all spelling errors
    2. Correct grammar mistakes
    3. Improve punctuation
    4. Make it more professional where needed
    5. Keep the original meaning and structure

    Language: {lang_name}

    IMPORTANT: Return ONLY the corrected text, no explanations or comments.

    CORRECTED TEXT:"""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': prompt}],
                options={
                    'temperature': 0.3,
                    'num_predict': 3000
                }
            )
            
            return response['message']['content']
        except Exception as e:
            return f"Error: {str(e)}"

    def _create_polish_prompt(self, cv_text, client_requirements, needs_translation=False, source_lang='polish'):
        """Polish prompt - complete with all fields populated"""
        prompt = "Jestes ekspertem HR specjalizujacym sie w analizie CV.\n\n"
        
        if needs_translation:
            prompt += f"WAZNE: CV jest napisane po {self._get_language_name(source_lang, 'pl')}. "
            prompt += "Przeanalizuj je i wygeneruj raport PO POLSKU, tlumaczac wszystkie informacje.\n\n"
        
        prompt += "TRESC CV KANDYDATA:\n" + cv_text + "\n\n"
        prompt += "WYMAGANIA KLIENTA:\n" + client_requirements + "\n\n"
        
        prompt += "Wygeneruj szczegolowy raport w formacie JSON PO POLSKU. WSZYSTKIE pola ponizej MUSZA byc wypelnione!\n"
        prompt += '{\n'
        
        prompt += '  "podstawowe_dane": {\n'
        prompt += '    "imie_nazwisko": "Wyciagnij z CV",\n'
        prompt += '    "email": "Email z CV lub: nie podano",\n'
        prompt += '    "telefon": "Telefon z CV lub: nie podano"\n'
        prompt += '  },\n'
        
        prompt += '  "lokalizacja_i_dostepnosc": {\n'
        prompt += '    "lokalizacja": "Miasto/Kraj z CV",\n'
        prompt += '    "preferencja_pracy_zdalnej": "Zdalna/Hybrydowa/Stacjonarna lub: nieokreslona",\n'
        prompt += '    "dostepnosc": "Okres wypowiedzenia lub: nieokreslona"\n'
        prompt += '  },\n'
        
        prompt += '  "podsumowanie_profilu": "WAZNE: Napisz WLASNA analize 3-5 zdan (nie kopiuj z CV!). Uwzglednij: doswiadczenie, kompetencje, dopasowanie do wymagan, rekomendacje (polecam/nie polecam).",\n'
        
        prompt += '  "doswiadczenie_zawodowe": [\n'
        prompt += '    {\n'
        prompt += '      "okres": "YYYY - YYYY lub YYYY - Obecnie",\n'
        prompt += '      "firma": "Nazwa firmy",\n'
        prompt += '      "stanowisko": "Stanowisko",\n'
        prompt += '      "kluczowe_osiagniecia": ["Lista osiagniec"],\n'
        prompt += '      "obowiazki": ["Obowiazki"],\n'
        prompt += '      "technologie": ["Technologie uzywane"]\n'
        prompt += '    }\n'
        prompt += '  ],\n'
        
        prompt += '  "wyksztalcenie": [\n'
        prompt += '    {\n'
        prompt += '      "uczelnia": "Nazwa uczelni",\n'
        prompt += '      "stopien": "Licencjat/Magister/Doktor",\n'
        prompt += '      "kierunek": "Kierunek studiow",\n'
        prompt += '      "okres": "YYYY - YYYY"\n'
        prompt += '    }\n'
        prompt += '  ],\n'
        
        prompt += '  "certyfikaty_i_kursy": [\n'
        prompt += '    {\n'
        prompt += '      "nazwa": "Nazwa certyfikatu/kursu",\n'
        prompt += '      "typ": "certyfikat lub kurs",\n'
        prompt += '      "wystawca": "Organizacja/Platforma",\n'
        prompt += '      "data": "Rok uzyskania"\n'
        prompt += '    }\n'
        prompt += '  ],\n'
        
        prompt += '  "jezyki_obce": [\n'
        prompt += '    {"jezyk": "Nazwa jezyka", "poziom": "A1/A2/B1/B2/C1/C2/Ojczysty"}\n'
        prompt += '  ],\n'
        prompt += '  "INSTRUKCJA_JEZYKI": "OBOWIAZKOWE! Szukaj wszystkich jezykow w CV. Zawsze dodaj jezyk ojczysty (Polski - Ojczysty jesli CV po polsku). Nie pomijaj!",\n'
        
        prompt += '  "umiejetnosci": {\n'
        prompt += '    "programowanie_skrypty": ["OBOWIAZKOWE! Wyciagnij WSZYSTKIE jezyki programowania z CV: Python, Java, C#, JavaScript, TypeScript, C++, Go, Ruby, PHP, Swift, Kotlin, Bash, PowerShell, itp."],\n'
        prompt += '    "frameworki_biblioteki": ["Wyciagnij frameworki/biblioteki wymienione w CV: Django, Flask, FastAPI, Spring, Express, NestJS, React, Angular, Vue, PyTorch, TensorFlow, Keras, Pandas, NumPy, Scikit-learn, H2O.ai, itp."],\n'
        prompt += '    "infrastruktura_devops": ["Docker, Kubernetes, Jenkins, GitLab CI, GitHub Actions, CircleCI, Git, Terraform, Ansible, Puppet, Chef, itp."],\n'
        prompt += '    "chmura": ["AWS, EC2, S3, Lambda, RDS, Azure, Virtual Machines, Blob Storage, Azure Functions, GCP, itp. - jesli brak: []"],\n'
        prompt += '    "bazy_kolejki": ["PostgreSQL, MySQL, MongoDB, Cassandra, Redis, Memcached, Kafka, RabbitMQ, Elasticsearch, Solr, itp."],\n'
        prompt += '    "monitoring": ["Prometheus, Grafana, Datadog, New Relic, ELK Stack, Kibana, Splunk, Fluentd, itp. - jesli brak: []"],\n'
        prompt += '    "inne": ["Agile, Scrum, Kanban, REST API, GraphQL, gRPC, OAuth, JWT, SAML, Linux, Nginx, Apache, SSL/TLS, itp."]\n'
        prompt += '  },\n'
        prompt += '  "INSTRUKCJA_SKILLS": "KRYTYCZNE! Szukaj KAZDEJ technologii w CV - nie pomijaj nic! Wymieniane sa w Skills, Work Experience, Projects. Wyciagaj tylko to co faktycznie jest w CV - NIGDY nie dodawaj udomyslonych!",\n'
        
        prompt += '  "podsumowanie_technologii": {\n'
        prompt += '    "opis": "Krotkie podsumowanie glownych technologii kandydata",\n'
        prompt += '    "glowne_technologie": ["8-10 najwazniejszych technologii"],\n'
        prompt += '    "lata_doswiadczenia": "X lat doswiadczenia w IT"\n'
        prompt += '  },\n'
        
        prompt += '  "dopasowanie_do_wymagan": {\n'
        prompt += '    "mocne_strony": ["Minimum 3 mocne strony"],\n'
        prompt += '    "poziom_dopasowania": "wysoki/sredni/niski",\n'
        prompt += '    "uzasadnienie": "Szczegolowe uzasadnienie",\n'
        prompt += '    "rekomendacja": "TAK/NIE"\n'
        prompt += '  }\n'
        prompt += '}\n\n'
        
        prompt += "ULTRA-KRYTYCZNE INSTRUKCJE:\n"
        prompt += "1. JEZYKI: Szukaj KAZDEGO jezyka wymienionego. Zawsze dodaj jezyk ojczysty!\n"
        prompt += "2. SKILLS: Wyciagnij WSZYSTKIE technologie z CV - nie pomijaj zadnej!\n"
        prompt += "3. CERTYFIKATY: Szukaj certyfikatow, kursow, szkolen - wszystko!\n"
        prompt += "4. TYLKO Z CV: Wyciagaj TYLKO co jest napisane - bez inferowania!\n"
        prompt += "5. ZWROC JSON: Poprawny JSON z WSZYSTKIMI polami wypelnionymi!\n"
        
        return prompt

    
    def _create_english_prompt(self, cv_text, client_requirements, needs_translation=False, source_lang='english'):
        """Updated English prompt - full anti-hallucination version"""
        prompt = "You are an expert HR professional specializing in CV analysis.\n\n"
        
        if needs_translation:
            prompt += f"IMPORTANT: CV is written in {self._get_language_name(source_lang, 'en')}. "
            prompt += "Analyze it and generate a comprehensive report IN ENGLISH, translating all information.\n\n"
        
        prompt += "CV TEXT:\n" + cv_text + "\n\n"
        prompt += "CLIENT REQUIREMENTS:\n" + client_requirements + "\n\n"
        
        prompt += "Generate a comprehensive report in JSON format IN ENGLISH:\n"
        prompt += '{\n'
        
        # Podstawowe dane
        prompt += '  "basic_data": {\n'
        prompt += '    "full_name": "Extract name and surname from CV",\n'
        prompt += '    "email": "Email or: not provided",\n'
        prompt += '    "phone": "Phone or: not provided"\n'
        prompt += '  },\n'
        
        # Location
        prompt += '  "location_and_availability": {\n'
        prompt += '    "location": "City/Country from CV",\n'
        prompt += '    "remote_work_preference": "Remote/Hybrid/On-site or: not specified",\n'
        prompt += '    "availability": "Notice period or: not specified"\n'
        prompt += '  },\n'
        
        # Profile summary
        prompt += '  "profile_summary": "IMPORTANT: Write YOUR OWN analysis (3-5 sentences), do NOT copy from CV. Include: experience, competencies, match to requirements, recommendation (recommend/do not recommend)",\n'
        
        # Work experience
        prompt += '  "work_experience": [\n'
        prompt += '    {\n'
        prompt += '      "period": "YYYY - YYYY or YYYY - Present",\n'
        prompt += '      "company": "Company name",\n'
        prompt += '      "position": "Position title",\n'
        prompt += '      "key_achievements": ["List of achievements with specific numbers/results"],\n'
        prompt += '      "responsibilities": ["Optional - detailed responsibilities"],\n'
        prompt += '      "technologies": ["MANDATORY - technologies used in this period"]\n'
        prompt += '    }\n'
        prompt += '  ],\n'
        
        # Education
        prompt += '  "education": [\n'
        prompt += '    {\n'
        prompt += '      "institution": "University name",\n'
        prompt += '      "degree": "Bachelor/Master/PhD",\n'
        prompt += '      "field": "Field of study",\n'
        prompt += '      "period": "YYYY - YYYY"\n'
        prompt += '    }\n'
        prompt += '  ],\n'
        prompt += '  "NOTE_EDUCATION": "If no education, return [] - NEVER skip this section!",\n'
        
        # Certifications and Courses
        prompt += '  "certifications_and_courses": [\n'
        prompt += '    {\n'
        prompt += '      "name": "Certification or course name",\n'
        prompt += '      "type": "certification or course",\n'
        prompt += '      "issuer": "Organization/Platform (AWS, Coursera, Udemy, edX)",\n'
        prompt += '      "date": "Year"\n'
        prompt += '    }\n'
        prompt += '  ],\n'
        prompt += '  "NOTE_CERTS": "Search for: professional certifications, online courses, training, workshops, bootcamps. If none, return []",\n'
        
        # Languages
        prompt += '  "languages": [\n'
        prompt += '    {"language": "Language name", "level": "A1/A2/B1/B2/C1/C2/Native"}\n'
        prompt += '  ],\n'
        prompt += '  "NOTE_LANGS": "ALWAYS add at least the native language. If CV is in English: add English - Native",\n'
        
        # Skills
        prompt += '  "skills": {\n'
        prompt += '    "programming_scripting": ["MANDATORY! Python, Java, C#, JavaScript, TypeScript, C++, Go, etc. NEVER empty!"],\n'
        prompt += '    "frameworks_libraries": ["Django, Flask, React, Angular, Spring, PyTorch, TensorFlow, Pandas, etc."],\n'
        prompt += '    "infrastructure_devops": ["Docker, Kubernetes, Git, Jenkins, GitLab CI, Terraform, Ansible, etc."],\n'
        prompt += '    "cloud": ["AWS, Azure, GCP, EC2, S3, Lambda, etc. - if none: []"],\n'
        prompt += '    "databases_messaging": ["PostgreSQL, MySQL, MongoDB, Redis, Kafka, RabbitMQ, Elasticsearch, etc."],\n'
        prompt += '    "monitoring": ["Prometheus, Grafana, ELK Stack, Datadog, etc. - if none: []"],\n'
        prompt += '    "other": ["Agile, Scrum, REST API, GraphQL, Linux, OAuth, JWT, etc."]\n'
        prompt += '  },\n'
        
        # Tech stack summary
        prompt += '  "tech_stack_summary": {\n'
        prompt += '    "description": "Brief summary of candidate main technologies",\n'
        prompt += '    "primary_technologies": ["Top 8-10 most important technologies"],\n'
        prompt += '    "years_of_experience": "X years of IT experience"\n'
        prompt += '  },\n'
        
        # Matching
        prompt += '  "matching_to_requirements": {\n'
        prompt += '    "strengths": ["At least 3 strengths related to requirements"],\n'
        prompt += '    "match_level": "high/medium/low",\n'
        prompt += '    "justification": "Detailed justification with specific examples",\n'
        prompt += '    "recommendation": "YES - recommend for further process / NO - does not meet requirements"\n'
        prompt += '  }\n'
        prompt += '}\n\n'
        
        prompt += "=" * 80 + "\n"
        prompt += "ULTRA-CRITICAL: EXTRACTION RULES - ZERO HALLUCINATIONS!\n"
        prompt += "=" * 80 + "\n"
        prompt += "\n"
        prompt += "MAIN RULE: Extract ONLY what is LITERALLY written in the CV!\n"
        prompt += "\n"
        prompt += "FORBIDDEN PRACTICES:\n"
        prompt += "- DO NOT infer technologies based on context\n"
        prompt += "- DO NOT add 'typical' technologies for a role\n"
        prompt += "- DO NOT use examples from this prompt as real data\n"
        prompt += "- DO NOT infer technologies from job title\n"
        prompt += "- If technology is NOT mentioned in CV, DO NOT add it!\n"
        prompt += "\n"
        prompt += "EXAMPLES OF MISTAKES (WHAT NOT TO DO):\n"
        prompt += "[ERROR 1] CV: 'Python' -> YOU ADD: Django, Flask (WRONG! Not in CV!)\n"
        prompt += "[ERROR 2] CV: 'Backend Developer' -> YOU ADD: JavaScript, Node.js (WRONG!)\n"
        prompt += "[ERROR 3] CV: 'ML Engineer' -> YOU ADD: TensorFlow, Keras (WRONG if not in CV!)\n"
        prompt += "[ERROR 4] CV: 'Git' -> YOU ADD: GitHub, GitLab (WRONG! Only Git!)\n"
        prompt += "\n"
        prompt += "CORRECT APPROACH:\n"
        prompt += "[CORRECT 1] CV: 'Python, Java, C#' -> YOU EXTRACT: ['Python', 'Java', 'C#']\n"
        prompt += "[CORRECT 2] CV: 'PyTorch and H2O.ai' -> YOU EXTRACT: ['PyTorch', 'H2O.ai']\n"
        prompt += "[CORRECT 3] CV: 'Git (good knowledge)' -> YOU EXTRACT: ['Git']\n"
        prompt += "[CORRECT 4] CV: 'Bash' -> YOU EXTRACT: ['Bash'] (NOT Linux, NOT Shell!)\n"
        prompt += "\n"
        prompt += "SPECIFIC INSTRUCTIONS FOR SKILLS:\n"
        prompt += "\n"
        prompt += "1. Programming & Scripting:\n"
        prompt += "   - Extract ONLY languages that are WRITTEN in CV\n"
        prompt += "   - If CV says 'Python, Java, C#' -> ONLY these 3!\n"
        prompt += "   - DO NOT add JavaScript if not in CV\n"
        prompt += "\n"
        prompt += "2. Frameworks & Libraries:\n"
        prompt += "   - Extract ONLY frameworks/libraries MENTIONED in CV\n"
        prompt += "   - DO NOT infer from languages (Python != Django automatically!)\n"
        prompt += "   - If CV says 'PyTorch, H2O.ai' -> ONLY these!\n"
        prompt += "\n"
        prompt += "3. Infrastructure & DevOps:\n"
        prompt += "   - Extract ONLY tools WRITTEN in CV\n"
        prompt += "   - Git != GitHub/GitLab (different things!)\n"
        prompt += "   - Docker != Kubernetes (don't add automatically!)\n"
        prompt += "\n"
        prompt += "VERIFICATION CHECKLIST BEFORE SUBMITTING:\n"
        prompt += "- Is EVERY technology I listed actually in the CV text?\n"
        prompt += "- Did I avoid adding 'common' technologies not mentioned?\n"
        prompt += "- Did I extract EXACTLY what's written, not what 'should' be there?\n"
        prompt += "- Did I double-check each item?\n"
        prompt += "\n"
        prompt += "IF IN DOUBT - DO NOT ADD!\n"
        prompt += "Better to omit than to hallucinate!\n"
        prompt += "\n"
        
        return prompt
    def translate_analysis_dict(analysis_dict, language="pl"):
        """Translate entire analysis dictionary to target language using LLM"""
        if language == "en":
            return analysis_dict  # No translation needed
        
        try:
            # Konwertuj dict do JSON string
            analysis_json = json.dumps(analysis_dict, ensure_ascii=False, indent=2)
            
            prompt = f"""Translate the following CV analysis from English to Polish.
    Keep all JSON structure intact. Keep names, dates, and technical terms unchanged.
    Only translate the text values.

    JSON to translate:
    {analysis_json}

    Respond ONLY with valid JSON, no other text."""
            
            response = ollama.generate(
                model="mistral",
                prompt=prompt,
                stream=False,
                temperature=0.1  # Low temperature for consistency
            )
            
            translated_text = response['response'].strip()
            
            # Spróbuj parsować JSON
            translated_dict = json.loads(translated_text)
            return translated_dict
            
        except Exception as e:
            print(f"Translation error: {e}")
            return analysis_dict  # Return original if translation fails


    def extract_key_highlights(self, analysis):
        """Extract REAL strengths with metrics and achievements"""
        highlights = []
        
        try:
            # 1. GŁOWNE STANOWISKO Z KONKRETNYMI DATAMI
            work_exp_data = analysis.get("doswiadczenie_zawodowe") or analysis.get("work_experience", [])
            
            if work_exp_data:
                job = work_exp_data[0]
                period = job.get("okres") or job.get("period", "")
                company = job.get("firma") or job.get("company", "")
                position = job.get("stanowisko") or job.get("position", "")
                
                if all([period, company, position]):
                    highlights.append(f"{position} at {company} ({period})")
            
            # 2. TOP OSIĄGNIĘCIA Z OPISEM - SZUKAJ KONKRETNYCH LICZB
            if work_exp_data:
                for job in work_exp_data[:2]:
                    achievements = job.get("kluczowe_osiagniecia") or job.get("key_achievements", [])
                    
                    if achievements:
                        # Weź PIERWSZE 2 osiągnięcia które mają liczby/procenty
                        for achievement in achievements[:3]:
                            achievement_str = str(achievement).strip()
                            
                            # Filtruj osiągnięcia z liczbami (konkretne rezultaty)
                            if any(char.isdigit() for char in achievement_str):
                                highlights.append(achievement_str)
                                if len(highlights) >= 5:
                                    break
                    
                    if len(highlights) >= 5:
                        break
            
            # 3. EDUKACJA Z SPECJALIZACJĄ
            if len(highlights) < 6:
                education = analysis.get("wyksztalcenie") or analysis.get("education", [])
                
                if education:
                    edu = education[0]
                    degree = edu.get("stopien") or edu.get("degree", "")
                    field = edu.get("kierunek") or edu.get("field", "")
                    
                    if degree and field:
                        highlights.append(f"Education: {degree} in {field}")
                    elif degree:
                        highlights.append(f"Education: {degree}")
            
            # 4. TOP TECHNOLOGIE (TYLKO WAŻNE!)
            if len(highlights) < 6:
                skills = analysis.get("umiejetnosci") or analysis.get("skills", {})
                
                if isinstance(skills, dict):
                    # Zbierz wszystkie techy
                    tech_list = []
                    
                    for key in ["programowanie_skrypty", "programming_scripting"]:
                        tech_list.extend(skills.get(key, []))
                    
                    for key in ["frameworki_biblioteki", "frameworks_libraries"]:
                        tech_list.extend(skills.get(key, []))
                    
                    # Filtruj TOP (najczęstsze, najważniejsze)
                    tech_list = [t for t in tech_list if t and len(str(t)) > 2][:5]
                    
                    if tech_list:
                        tech_str = ", ".join([str(t) for t in tech_list])
                        highlights.append(f"Core Technologies: {tech_str}")
            
            # 5. LATA DOŚWIADCZENIA
            if len(highlights) < 6:
                years = analysis.get("lata_doswiadczenia") or analysis.get("years_experience", 0)
                
                if years and int(float(years)) > 0:
                    highlights.append(f"{int(float(years))}+ years in IT and Data Science")
            
            # 6. CERTYFIKATY - KONKRETNE
            if len(highlights) < 6:
                certs = analysis.get("certyfikaty_i_kursy") or analysis.get("certifications_and_courses", [])
                
                if certs:
                    top_certs = []
                    for cert in certs[:3]:
                        cert_name = cert.get("nazwa") or cert.get("name", "")
                        cert_issuer = cert.get("wystawca") or cert.get("issuer", "")
                        
                        if cert_name:
                            if cert_issuer:
                                top_certs.append(f"{cert_name} ({cert_issuer})")
                            else:
                                top_certs.append(cert_name)
                    
                    if top_certs:
                        highlights.append(f"Certifications: {', '.join(top_certs[:2])}")
            
            # Ogranicz do 6 i czyszcz pusty text
            highlights = [h for h in highlights if h and len(str(h).strip()) > 5]
            return highlights[:6]
        
        except Exception as e:
            print(f"Error in extract_key_highlights: {e}")
            return []

    def _get_language_name(self, lang_code, output_lang):
        """Get language name in specified language"""
        names = {
            'polish': {'pl': 'polsku', 'en': 'Polish'},
            'english': {'pl': 'angielsku', 'en': 'English'}
        }
        return names.get(lang_code, {}).get(output_lang, lang_code)
    
    def generate_pdf_output(self, analysis, template_type='full', language=None):
        """Generate PDF with FPDF2 - Arsenal font - 2 pages layout"""
        
        filtered_analysis = self.apply_template_filters(analysis, template_type)
        if language is None:
            language = filtered_analysis.get('output_language', 'en')
        # Font paths
        arsenal_regular = r"C:\Users\Kamil Czyżewski\OneDrive - Integral Solutions sp. z o.o\Pulpit\arsenal\Arsenal-Regular.ttf"
        arsenal_bold = r"C:\Users\Kamil Czyżewski\OneDrive - Integral Solutions sp. z o.o\Pulpit\arsenal\Arsenal-Bold.ttf"
        
        def safe_text(text):
            if text is None:
                return 'N/A'
            return str(text)
        
        def get_section_name(en_name):
            """Polish translation"""
            output_lang = filtered_analysis.get('output_language', 'english')
            
            translations = {
                'K E Y H I G H L I G H T S':'G Ł Ó W N E  O S I Ą G N I Ę C I A',
                'E D U C A T I O N': 'W Y K S Z T A Ł C E N I E',
                'L A N G U A G E S': 'J Ę Z Y K I',
                'C E R T I F I C A T I O N S': 'C E R T Y F I K A T Y',
                'P R O F I L E  S U M M A R Y': 'P O D S U M O W A N I E  P R O F I L U',
                'S K I L L S': 'U M I E J Ę T N O Ś C I',
                'T E C H  S T A C K': 'T E C H N O L O G I E',
                'W O R K  E X P E R I E N C E': 'D O Ś W I A D C Z E N I E  Z A W O D O W E',
                
            }
            
            if output_lang == 'polish':
                return translations.get(en_name, en_name)
            return en_name
        
        # Get data
        work_exp_data = filtered_analysis.get("doswiadczenie_zawodowe") or filtered_analysis.get("work_experience", [])
        
        candidate_name = "CANDIDATE NAME"
        candidate_title = "Professional Title"
        
        if "podstawowe_dane" in filtered_analysis:
            candidate_name = safe_text(filtered_analysis["podstawowe_dane"].get('imie_nazwisko', 'CANDIDATE NAME')).upper()
        elif "personal_data" in filtered_analysis or "basic_data" in filtered_analysis:
                # ← DODAJ TEN WARUNEK DLA ANGIELSKIEJ WERSJI
            basic = filtered_analysis.get("personal_data") or filtered_analysis.get("basic_data")
            if basic:
                candidate_name = safe_text(basic.get('full_name') or basic.get('name') or 'CANDIDATE NAME').upper()
            
        if work_exp_data:
            candidate_title = safe_text(work_exp_data[0].get('stanowisko') or work_exp_data[0].get('position', 'Professional'))
        
        # Create PDF
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        # Rejestruj czcionki
        try:
            pdf.add_font('Arsenal', '', arsenal_regular)
            pdf.add_font('Arsenal', 'B', arsenal_bold)
        except Exception as e:
            print(f"Font error: {e}")
            pdf.set_font('DejaVu', '', 10)
        
        # Set margins
        pdf.set_margins(left=12.7, top=0, right=12.7)
        
        # ===== PAGE 1: HEADER + PROFILE SUMMARY (BULLET POINTS ONLY) =====
        
        # Blue header
        pdf.set_fill_color(50, 130, 180)
        pdf.rect(0, 0, 210, 40, 'F')
        
        # Logo
        logo_path = r"C:\Users\Kamil Czyżewski\OneDrive - Integral Solutions sp. z o.o\Pulpit\IS_New 1.png"
        try:
            pdf.image(logo_path, x=5, y=9, w=50)
        except Exception as e:
            print(f"Logo error: {e}")
        
        # Name - centered
        pdf.set_font('Arsenal', 'B', 24)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(0, 12)
        pdf.cell(0, 8, candidate_name, align='C')
        
        # Title - centered
        pdf.set_font('Arsenal', '', 12)
        pdf.set_xy(0, 22)
        pdf.cell(0, 8, candidate_title, align='C')
        
        # Back to black
        pdf.set_text_color(0, 0, 0)
        
        # Move down after header
        pdf.set_y(50)
        pdf.set_x(12.7)
        
        # ===== GENERATE KEY HIGHLIGHTS FROM PROFILE SUMMARY =====
        profile_summary = filtered_analysis.get("podsumowanie_profilu") or filtered_analysis.get("profile_summary") or ""
        
        if profile_summary and not filtered_analysis.get("mocne_strony"):
            # Split by bullets or sentences to generate highlights
            highlights = [h.strip() for h in profile_summary.split('•') if h.strip()]
            if not highlights:
                highlights = [s.strip() for s in profile_summary.split('.') if s.strip()][:6]
            filtered_analysis['mocne_strony'] = highlights[:6]
        
        # ===== DISPLAY KEY HIGHLIGHTS ON PAGE 1 =====
        highlights = filtered_analysis.get("key_highlights", [])

        # DEBUG: Sprawdź co jest w key_highlights
        print(f"DEBUG key_highlights: {highlights}")
        print(f"DEBUG type: {type(highlights)}")

        # Zawsze wyświetlaj highlights, nawet jeśli są puste - wygeneruj je z profile_summary
        if not highlights or len(highlights) == 0:
            # Wygeneruj bullet points z profile_summary
            profile_text = filtered_analysis.get("podsumowanie_profilu") or filtered_analysis.get("profile_summary") or ""
            
            if profile_text and profile_text.strip():
                # Split by bullets lub zdania
                if "•" in profile_text:
                    highlights = [h.strip() for h in profile_text.split("•") if h.strip()][:6]
                else:
                    # Split by sentences
                    sentences = [s.strip() for s in profile_text.split(".") if len(s.strip()) > 10]
                    highlights = sentences[:6]
                
                print(f"DEBUG generated highlights: {highlights}")

        # Teraz zawsze wyświetl
        if highlights:
            pdf.set_font('Arsenal', 'B', 11)
            # Domyślnie 'en' jeśli brak parametru
            pdf_language = language if language else 'en'
            pdf.cell(0, 5, get_section_name('K E Y H I G H L I G H T S'), ln=True)
            
            # Underline
            pdf.set_draw_color(76, 76, 76)
            pdf.set_line_width(0.3)
            y_before = pdf.get_y()
            pdf.line(12.7, y_before, 197.3, y_before)
            pdf.set_draw_color(0, 0, 0)
            
            pdf.set_y(y_before + 3)
            pdf.set_x(12.7)
            
            pdf.set_font('Arsenal', '', 9)
            
            for highlight in highlights:
                highlight_text = safe_text(highlight).strip()
                if highlight_text:
                    pdf.set_x(12.7)
                    pdf.multi_cell(0, 4, f"• {highlight_text}", align='L')
        else:
            # If no highlights, show plain profile summary
            profile_text = filtered_analysis.get("podsumowanie_profilu") or filtered_analysis.get("profile_summary") or ""
            if profile_text:
                pdf.set_font('Arsenal', 'B', 11)
                pdf.cell(0, 5, get_section_name('P R O F I L E  S U M M A R Y'), ln=True)
                
                # Underline
                pdf.set_draw_color(76, 76, 76)
                pdf.set_line_width(0.3)
                y_before = pdf.get_y()
                pdf.line(12.7, y_before, 197.3, y_before)
                pdf.set_draw_color(0, 0, 0)
                
                pdf.set_y(y_before + 3)
                pdf.set_x(12.7)
                pdf.set_font('Arsenal', '', 9)
                pdf.multi_cell(0, 4, profile_text, align='L')
        
        # ===== PAGE 2: TWO COLUMNS LAYOUT - NEW ORDER =====
        pdf.add_page()
        pdf.set_margins(left=12.7, top=0, right=12.7)
        
        # Blue header (repeat on page 2)
        pdf.set_fill_color(50, 130, 180)
        pdf.rect(0, 0, 210, 40, 'F')
        
        # Logo
        try:
            pdf.image(logo_path, x=5, y=9, w=50)
        except Exception as e:
            print(f"Logo error: {e}")
        
        # Name
        pdf.set_font('Arsenal', 'B', 24)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(0, 12)
        pdf.cell(0, 8, candidate_name, align='C')
        
        # Title
        pdf.set_font('Arsenal', '', 12)
        pdf.set_xy(0, 22)
        pdf.cell(0, 8, candidate_title, align='C')
        
        # Back to black
        pdf.set_text_color(0, 0, 0)
        
        # Move down
        pdf.set_y(50)
        
        # ===== TWO COLUMN LAYOUT - NEW ORDER =====
        col_left_x = 12.7
        col_right_x = 100
        
        col_left_width = 80
        col_right_width = 97.3
        
        def add_section_header(x, title, max_width):
            """Add section header with underline"""
            pdf.set_font('Arsenal', 'B', 10)
            pdf.set_xy(x, pdf.get_y())
            pdf.multi_cell(max_width, 5, title)
            
            pdf.set_draw_color(76, 76, 76)
            pdf.set_line_width(0.3)
            y_pos = pdf.get_y()
            pdf.line(x, y_pos, x + max_width - 2, y_pos)
            pdf.set_draw_color(0, 0, 0)
            
            return y_pos + 3
        
        def add_text_column(x, text, font_size=8, max_width=45):
            """Add wrapped text to column"""
            pdf.set_font('Arsenal', '', font_size)
            pdf.set_xy(x, pdf.get_y())
            pdf.multi_cell(max_width, 4, text, align='L')
        
        def add_bold_text_column(x, text, font_size=8, max_width=45):
            """Add bold wrapped text to column"""
            pdf.set_font('Arsenal', 'B', font_size)
            pdf.set_xy(x, pdf.get_y())
            pdf.multi_cell(max_width, 4, text, align='L')
        
        # ===== LEFT COLUMN: SKILLS, TECH STACK, LANGUAGES, CERTIFICATIONS =====
        
        # SKILLS
        skills_data = filtered_analysis.get("umiejetnosci") or filtered_analysis.get("skills")
        if skills_data:
            pdf.set_xy(col_left_x, 50)
            y_left = add_section_header(col_left_x, get_section_name('S K I L L S'), col_left_width)
            pdf.set_y(y_left)
            
            skill_cats = [
                ('programowanie_skrypty', 'programming_scripting', 'Programming'),
                ('frameworki_biblioteki', 'frameworks_libraries', 'Frameworks'),
                ('infrastruktura_devops', 'infrastructure_devops', 'Infrastructure'),
                ('chmura', 'cloud', 'Cloud'),
                ('bazy_kolejki', 'data_messaging', 'Data'),
                ('monitoring', 'monitoring', 'Monitoring'),
            ]
            
            for pl_key, en_key, label in skill_cats:
                skills_list = skills_data.get(pl_key) or skills_data.get(en_key)
                if skills_list:
                    skills_str = ', '.join([safe_text(s) for s in skills_list])
                    pdf.set_xy(col_left_x + 2, pdf.get_y())
                    add_bold_text_column(col_left_x + 2, f"{label}:", 7, col_left_width - 4)
                    pdf.set_xy(col_left_x + 2, pdf.get_y())
                    add_text_column(col_left_x + 2, skills_str, 7, col_left_width - 4)
            
            pdf.set_y(pdf.get_y() + 2)
        
        # TECH STACK
        tech_summary = filtered_analysis.get("podsumowanie_technologii") or filtered_analysis.get("tech_stack_summary")
        if tech_summary:
            pdf.set_xy(col_left_x, pdf.get_y())
            y_left = add_section_header(col_left_x, get_section_name('T E C H  S T A C K'), col_left_width)
            pdf.set_y(y_left)
            description = tech_summary.get('opis') or tech_summary.get('description')
            if description:
                pdf.set_xy(col_left_x + 2, pdf.get_y())
                add_text_column(col_left_x + 2, safe_text(description), 7, col_left_width - 4)
                pdf.set_y(pdf.get_y() + 2)
        
        # LANGUAGES
        languages_data = filtered_analysis.get("jezyki_obce") or filtered_analysis.get("languages", [])
        if languages_data:
            pdf.set_xy(col_left_x, pdf.get_y())
            y_left = add_section_header(col_left_x, get_section_name('L A N G U A G E S'), col_left_width)
            pdf.set_y(y_left)
            
            for lang in languages_data:
                language = safe_text(lang.get('jezyk') or lang.get('language', ''))
                level = safe_text(lang.get('poziom') or lang.get('level', ''))
                pdf.set_xy(col_left_x + 2, pdf.get_y())
                add_text_column(col_left_x + 2, f"{language}: {level}", 7, col_left_width - 4)
            
            pdf.set_y(pdf.get_y() + 2)
        
        # CERTIFICATIONS
        certs_and_courses = (
            filtered_analysis.get("certyfikaty_i_kursy") or 
            filtered_analysis.get("certifications_and_courses") or
            (filtered_analysis.get("certyfikaty", []) or []) + (filtered_analysis.get("certifications", []) or [])
        )
        
        if certs_and_courses:
            pdf.set_xy(col_left_x, pdf.get_y())
            y_left = add_section_header(col_left_x, get_section_name('C E R T I F I C A T I O N S'), col_left_width)
            pdf.set_y(y_left)
            
            for item in certs_and_courses:
                item_name = safe_text(item.get('nazwa') or item.get('name', ''))
                issuer = safe_text(item.get('wystawca') or item.get('issuer', ''))
                
                pdf.set_xy(col_left_x + 2, pdf.get_y())
                add_bold_text_column(col_left_x + 2, item_name, 7, col_left_width - 4)
                pdf.set_xy(col_left_x + 2, pdf.get_y())
                add_text_column(col_left_x + 2, issuer, 6, col_left_width - 4)
            
            pdf.set_y(pdf.get_y() + 2)
        
        # ===== RIGHT COLUMN: PROFILE SUMMARY (FULL TEXT), WORK EXPERIENCE, EDUCATION =====
        
        # PROFILE SUMMARY - FULL TEXT (na drugiej stronie)
        if profile_summary:
            pdf.set_xy(col_right_x, 50)
            y_right = add_section_header(col_right_x, get_section_name('P R O F I L E  S U M M A R Y'), col_right_width)
            pdf.set_y(y_right)
            
            # Cały tekst bez bullet points
            profile_text = safe_text(profile_summary)
            # Usuń bullet points jeśli są
            profile_text = profile_text.replace('•', '').strip()
            
            pdf.set_xy(col_right_x + 2, pdf.get_y())
            add_text_column(col_right_x + 2, profile_text, 7, col_right_width - 4)
            pdf.set_y(pdf.get_y() + 2)
        
        # WORK EXPERIENCE
        if work_exp_data:
            pdf.set_xy(col_right_x, pdf.get_y())
            y_right = add_section_header(col_right_x, get_section_name('W O R K  E X P E R I E N C E'), col_right_width)
            pdf.set_y(y_right)
            
            for exp in work_exp_data:
                period = safe_text(exp.get('okres') or exp.get('period', 'N/A'))
                company = safe_text(exp.get('firma') or exp.get('company', ''))
                position = safe_text(exp.get('stanowisko') or exp.get('position', ''))
                
                pdf.set_xy(col_right_x + 2, pdf.get_y())
                add_bold_text_column(col_right_x + 2, f"{period} - {company}", 8, col_right_width - 4)
                pdf.set_xy(col_right_x + 2, pdf.get_y())
                add_text_column(col_right_x + 2, position, 7, col_right_width - 4)
                
                achievements = exp.get('kluczowe_osiagniecia') or exp.get('key_achievements', [])
                if achievements:
                    for achievement in achievements:
                        pdf.set_xy(col_right_x + 2, pdf.get_y())
                        add_text_column(col_right_x + 2, f"• {safe_text(achievement)}", 7, col_right_width - 4)
                
                pdf.set_y(pdf.get_y() + 2)
        
        # EDUCATION
        education_data = filtered_analysis.get("wyksztalcenie") or filtered_analysis.get("education", [])
        if education_data:
            pdf.set_xy(col_right_x, pdf.get_y())
            y_right = add_section_header(col_right_x, get_section_name('E D U C A T I O N'), col_right_width)
            pdf.set_y(y_right)
            
            for edu in education_data:
                institution = safe_text(edu.get('uczelnia') or edu.get('institution', ''))
                degree = safe_text(edu.get('stopien') or edu.get('degree', ''))
                field = safe_text(edu.get('kierunek') or edu.get('field', ''))
                period = safe_text(edu.get('okres') or edu.get('period', ''))
                
                pdf.set_xy(col_right_x + 2, pdf.get_y())
                add_bold_text_column(col_right_x + 2, institution, 7, col_right_width - 4)
                pdf.set_xy(col_right_x + 2, pdf.get_y())
                add_text_column(col_right_x + 2, f"{degree} of {field}", 7, col_right_width - 4)
                pdf.set_xy(col_right_x + 2, pdf.get_y())
                add_text_column(col_right_x + 2, period, 7, col_right_width - 4)
                pdf.set_y(pdf.get_y() + 2)
        # ===== GENERATE KEY HIGHLIGHTS FROM PROFILE SUMMARY =====
        profile_text = filtered_analysis.get("podsumowanie_profilu") or filtered_analysis.get("profile_summary") or ""
        
        # Generate highlights if they don't exist yet
        if profile_text and not filtered_analysis.get("mocne_strony"):
            # Try splitting by bullets first
            highlights = [h.strip() for h in profile_text.split('•') if h.strip()]
            
            # If no bullets, split by sentences
            if not highlights or len(highlights) < 2:
                sentences = [s.strip() for s in profile_text.split('.') if s.strip()]
                highlights = sentences[:6]
            
            filtered_analysis['mocne_strony'] = highlights[:6] if highlights else []
        # Save to buffer
        buffer = BytesIO()
        pdf.output(buffer)
        buffer.seek(0)
        return buffer
    
    def generate_docx_output(self, analysis, template_type='full', language=None):
        """Generate DOCX with Arsenal font - all headers with underlines"""
        
        filtered_analysis = self.apply_template_filters(analysis, template_type)
        if language is None:
            language = filtered_analysis.get('output_language', 'en')
        
        # Arsenal font path
        arsenal_regular = r"C:\Users\Kamil Czyżewski\OneDrive - Integral Solutions sp. z o.o\Pulpit\arsenal\Arsenal-Regular.ttf"
        
        def safe_text(text):
            if text is None:
                return 'N/A'
            return str(text)
        
        def get_section_name(en_name):
            output_lang = filtered_analysis.get('output_language', 'english')
            translations = {
                'K E Y H I G H L I G H T S': 'G Ł Ó W N E  O S I Ą G N I Ę C I A',
                'E D U C A T I O N': 'W Y K S Z T A Ł C E N I E',
                'L A N G U A G E S': 'J Ę Z Y K I',
                'C E R T I F I C A T I O N S': 'C E R T Y F I K A T Y',
                'P R O F I L E  S U M M A R Y': 'P O D S U M O W A N I E  P R O F I L U',
                'S K I L L S': 'U M I E J Ę T N O Ś C I',
                'T E C H  S T A C K': 'T E C H N O L O G I E',
                'W O R K  E X P E R I E N C E': 'D O Ś W I A D C Z E N I E  Z A W O D O W E',
            }
            if output_lang == 'polish':
                return translations.get(en_name, en_name)
            return en_name
        
        def apply_arsenal_font(run, size=9, bold=False):
            """Apply Arsenal font styling"""
            run.font.name = 'Arsenal'
            run.font.size = Pt(size)
            if bold:
                run.font.bold = True
        
        def add_section_header_with_underline(cell, title):
            """Add header with underline using Arsenal font"""
            p = cell.add_paragraph()
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(2)
            
            run = p.add_run(title)
            apply_arsenal_font(run, size=10, bold=True)
            
            # Add underline
            pPr = p._element.get_or_add_pPr()
            pBdr = parse_xml(r'<w:pBdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:bottom w:val="single" w:sz="12" w:space="1" w:color="4C4C4C"/></w:pBdr>')
            pPr.append(pBdr)
            
            return p
        
        def create_full_width_header(doc, candidate_name, candidate_title):
            """Create full-width blue header"""
            header_table = doc.add_table(rows=1, cols=1)
            tbl = header_table._element
            tblPr = tbl.tblPr
            
            tblW = OxmlElement('w:tblW')
            tblW.set(qn('w:w'), '6500')
            tblW.set(qn('w:type'), 'pct')
            tblPr.append(tblW)
            
            tblInd = OxmlElement('w:tblInd')
            tblInd.set(qn('w:w'), '-1440')
            tblInd.set(qn('w:type'), 'dxa')
            tblPr.append(tblInd)
            
            tblBorders = OxmlElement('w:tblBorders')
            for border_name in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
                border = OxmlElement(f'w:{border_name}')
                border.set(qn('w:val'), 'none')
                border.set(qn('w:sz'), '0')
                border.set(qn('w:space'), '0')
                border.set(qn('w:color'), 'auto')
                tblBorders.append(border)
            tblPr.append(tblBorders)
            
            tblCellMar = OxmlElement('w:tblCellMar')
            for margin_type in ['top', 'left', 'bottom', 'right']:
                margin = OxmlElement(f'w:{margin_type}')
                margin.set(qn('w:w'), '0')
                margin.set(qn('w:type'), 'dxa')
                tblCellMar.append(margin)
            tblPr.append(tblCellMar)
            
            header_cell = header_table.rows[0].cells[0]
            shading_elm = parse_xml(r'<w:shd {} w:fill="3282B4"/>'.format('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'))
            header_cell._element.get_or_add_tcPr().append(shading_elm)
            
            header_para = header_cell.paragraphs[0]
            header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            header_para.paragraph_format.space_before = Pt(15)
            header_para.paragraph_format.space_after = Pt(5)
            
            name_run = header_para.add_run(candidate_name)
            apply_arsenal_font(name_run, size=28, bold=True)
            name_run.font.color.rgb = RGBColor(255, 255, 255)
            
            title_para = header_cell.add_paragraph()
            title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            title_para.paragraph_format.space_before = Pt(0)
            title_para.paragraph_format.space_after = Pt(15)
            
            title_run = title_para.add_run(candidate_title)
            apply_arsenal_font(title_run, size=13, bold=False)
            title_run.font.color.rgb = RGBColor(255, 255, 255)
        
        work_exp_data = filtered_analysis.get("doswiadczenie_zawodowe") or filtered_analysis.get("work_experience", [])
        
        candidate_name = "CANDIDATE NAME"
        candidate_title = "Professional Title"
        
        if "podstawowe_dane" in filtered_analysis:
            candidate_name = safe_text(filtered_analysis["podstawowe_dane"].get('imie_nazwisko', 'CANDIDATE NAME')).upper()
        elif "personal_data" in filtered_analysis or "basic_data" in filtered_analysis:
                # ← DODAJ TEN WARUNEK DLA ANGIELSKIEJ WERSJI
            basic = filtered_analysis.get("personal_data") or filtered_analysis.get("basic_data")
            if basic:
                candidate_name = safe_text(basic.get('full_name') or basic.get('name') or 'CANDIDATE NAME').upper()
            
        if work_exp_data:
            candidate_title = safe_text(work_exp_data[0].get('stanowisko') or work_exp_data[0].get('position', 'Professional'))
        
        doc = Document()
        
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(0)
            section.bottom_margin = Inches(0.3)
            section.left_margin = Inches(0.5)
            section.right_margin = Inches(0.5)
        
        # ===== PAGE 1 =====
        create_full_width_header(doc, candidate_name, candidate_title)
        doc.add_paragraph()
        
        profile_summary = filtered_analysis.get("podsumowanie_profilu") or filtered_analysis.get("profile_summary") or ""
        
        if profile_summary and not filtered_analysis.get("mocne_strony"):
            highlights = [h.strip() for h in profile_summary.split('•') if h.strip()]
            if not highlights:
                highlights = [s.strip() for s in profile_summary.split('.') if s.strip()][:6]
            filtered_analysis['mocne_strony'] = highlights[:6]
        
        highlights = filtered_analysis.get("key_highlights", [])
        
        if not highlights or len(highlights) == 0:
            profile_text = filtered_analysis.get("podsumowanie_profilu") or filtered_analysis.get("profile_summary") or ""
            if profile_text and profile_text.strip():
                if "•" in profile_text:
                    highlights = [h.strip() for h in profile_text.split("•") if h.strip()][:6]
                else:
                    sentences = [s.strip() for s in profile_text.split(".") if len(s.strip()) > 10]
                    highlights = sentences[:6]
        
        # PAGE 1 - KEY HIGHLIGHTS WITH UNDERLINE
        heading = doc.add_paragraph()
        run = heading.add_run(get_section_name('K E Y H I G H L I G H T S'))
        apply_arsenal_font(run, size=11, bold=True)
        
        pPr = heading._element.get_or_add_pPr()
        pBdr = parse_xml(r'<w:pBdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:bottom w:val="single" w:sz="12" w:space="1" w:color="4C4C4C"/></w:pBdr>')
        pPr.append(pBdr)
        
        if highlights:
            for highlight in highlights:
                highlight_text = safe_text(highlight).strip()
                if highlight_text:
                    p = doc.add_paragraph(highlight_text, style='List Bullet')
                    for run in p.runs:
                        apply_arsenal_font(run, size=9, bold=False)
        
        doc.add_page_break()
        
        # ===== PAGE 2: TWO COLUMNS =====
        create_full_width_header(doc, candidate_name, candidate_title)
        doc.add_paragraph()
        
        page2_table = doc.add_table(rows=1, cols=2)
        page2_table.autofit = False
        
        left_cell = page2_table.rows[0].cells[0]
        right_cell = page2_table.rows[0].cells[1]
        
        # Clear existing paragraphs
        for paragraph in list(left_cell.paragraphs):
            p = paragraph._element
            p.getparent().remove(p)
        for paragraph in list(right_cell.paragraphs):
            p = paragraph._element
            p.getparent().remove(p)
        
        # ===== LEFT COLUMN =====
        
        # SKILLS WITH UNDERLINE
        add_section_header_with_underline(left_cell, get_section_name('S K I L L S'))
        
        skills_data = filtered_analysis.get("umiejetnosci") or filtered_analysis.get("skills")
        if skills_data:
            skill_cats = [
                ('programowanie_skrypty', 'programming_scripting', 'Programming'),
                ('frameworki_biblioteki', 'frameworks_libraries', 'Frameworks'),
                ('infrastruktura_devops', 'infrastructure_devops', 'Infrastructure'),
                ('chmura', 'cloud', 'Cloud'),
                ('bazy_kolejki', 'data_messaging', 'Data'),
                ('monitoring', 'monitoring', 'Monitoring'),
            ]
            
            for pl_key, en_key, label in skill_cats:
                skills_list = skills_data.get(pl_key) or skills_data.get(en_key)
                if skills_list:
                    skills_str = ', '.join([safe_text(s) for s in skills_list])
                    
                    p = left_cell.add_paragraph(f"{label}:")
                    p.paragraph_format.space_before = Pt(0)
                    p.paragraph_format.space_after = Pt(0)
                    for run in p.runs:
                        apply_arsenal_font(run, size=7, bold=True)
                    
                    p = left_cell.add_paragraph(skills_str)
                    p.paragraph_format.space_before = Pt(0)
                    p.paragraph_format.space_after = Pt(0)
                    for run in p.runs:
                        apply_arsenal_font(run, size=7, bold=False)
        
        # TECH STACK WITH UNDERLINE
        p = left_cell.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(0)
        add_section_header_with_underline(left_cell, get_section_name('T E C H  S T A C K'))
        
        tech_summary = filtered_analysis.get("podsumowanie_technologii") or filtered_analysis.get("tech_stack_summary")
        if tech_summary:
            description = tech_summary.get('opis') or tech_summary.get('description')
            if description:
                p = left_cell.add_paragraph(safe_text(description))
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                for run in p.runs:
                    apply_arsenal_font(run, size=7, bold=False)
        
        # LANGUAGES WITH UNDERLINE
        p = left_cell.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(0)
        add_section_header_with_underline(left_cell, get_section_name('L A N G U A G E S'))
        
        languages_data = filtered_analysis.get("jezyki_obce") or filtered_analysis.get("languages", [])
        if languages_data:
            for lang in languages_data:
                language = safe_text(lang.get('jezyk') or lang.get('language', ''))
                level = safe_text(lang.get('poziom') or lang.get('level', ''))
                
                p = left_cell.add_paragraph(f"{language}: {level}")
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                for run in p.runs:
                    apply_arsenal_font(run, size=7, bold=False)
        
        # CERTIFICATIONS WITH UNDERLINE
        p = left_cell.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(0)
        add_section_header_with_underline(left_cell, get_section_name('C E R T I F I C A T I O N S'))
        
        certs_and_courses = (
            filtered_analysis.get("certyfikaty_i_kursy") or 
            filtered_analysis.get("certifications_and_courses") or
            (filtered_analysis.get("certyfikaty", []) or []) + (filtered_analysis.get("certifications", []) or [])
        )
        
        if certs_and_courses:
            for item in certs_and_courses:
                item_name = safe_text(item.get('nazwa') or item.get('name', ''))
                issuer = safe_text(item.get('wystawca') or item.get('issuer', ''))
                
                p = left_cell.add_paragraph(item_name)
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                for run in p.runs:
                    apply_arsenal_font(run, size=7, bold=True)
                
                p = left_cell.add_paragraph(issuer)
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                for run in p.runs:
                    apply_arsenal_font(run, size=6, bold=False)
        
        # ===== RIGHT COLUMN =====
        
        # PROFILE SUMMARY WITH UNDERLINE
        add_section_header_with_underline(right_cell, get_section_name('P R O F I L E  S U M M A R Y'))
        
        if profile_summary:
            profile_text = safe_text(profile_summary).replace('•', '').strip()
            p = right_cell.add_paragraph(profile_text)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            for run in p.runs:
                apply_arsenal_font(run, size=7, bold=False)
        
        # WORK EXPERIENCE WITH UNDERLINE
        p = right_cell.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(0)
        add_section_header_with_underline(right_cell, get_section_name('W O R K  E X P E R I E N C E'))
        
        if work_exp_data:
            for exp in work_exp_data:
                period = safe_text(exp.get('okres') or exp.get('period', 'N/A'))
                company = safe_text(exp.get('firma') or exp.get('company', ''))
                position = safe_text(exp.get('stanowisko') or exp.get('position', ''))
                
                p = right_cell.add_paragraph(f"{period} - {company}")
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                for run in p.runs:
                    apply_arsenal_font(run, size=8, bold=True)
                
                p = right_cell.add_paragraph(position)
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                for run in p.runs:
                    apply_arsenal_font(run, size=7, bold=False)
                
                achievements = exp.get('kluczowe_osiagniecia') or exp.get('key_achievements', [])
                if achievements:
                    for achievement in achievements:
                        p = right_cell.add_paragraph(safe_text(achievement), style='List Bullet')
                        p.paragraph_format.space_before = Pt(0)
                        p.paragraph_format.space_after = Pt(0)
                        for run in p.runs:
                            apply_arsenal_font(run, size=7, bold=False)
        
        # EDUCATION WITH UNDERLINE
        p = right_cell.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(0)
        add_section_header_with_underline(right_cell, get_section_name('E D U C A T I O N'))
        
        education_data = filtered_analysis.get("wyksztalcenie") or filtered_analysis.get("education", [])
        if education_data:
            for edu in education_data:
                institution = safe_text(edu.get('uczelnia') or edu.get('institution', ''))
                degree = safe_text(edu.get('stopien') or edu.get('degree', ''))
                field = safe_text(edu.get('kierunek') or edu.get('field', ''))
                period = safe_text(edu.get('okres') or edu.get('period', ''))
                
                p = right_cell.add_paragraph(institution)
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                for run in p.runs:
                    apply_arsenal_font(run, size=7, bold=True)
                
                p = right_cell.add_paragraph(f"{degree} of {field}")
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                for run in p.runs:
                    apply_arsenal_font(run, size=7, bold=False)
                
                p = right_cell.add_paragraph(period)
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                for run in p.runs:
                    apply_arsenal_font(run, size=7, bold=False)
        
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer