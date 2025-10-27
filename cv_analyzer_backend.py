import pymupdf
from PIL import Image
import pytesseract
import ollama
import json
import os
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from io import BytesIO

from reportlab.lib.enums import TA_LEFT
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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

    def apply_template_filters(self, analysis, template_type):
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
        """Prompt for Polish output with enhanced candidate strengths analysis"""
        prompt = "Jestes ekspertem HR specjalizujacym sie w analizie CV i dopasowywaniu kandydatow do wymaган.\n\n"
        
        if needs_translation:
            prompt += f"WAZNE: CV jest napisane po {self._get_language_name(source_lang, 'pl')}. "
            prompt += "Przeanalizuj je i wygeneruj raport PO POLSKU, tlumaczac wszystkie informacje.\n\n"
        
        prompt += "TRESC CV KANDYDATA:\n" + cv_text + "\n\n"
        prompt += "WYMAGANIA KLIENTA:\n" + client_requirements + "\n\n"
        
        prompt += "ZADANIE: Przeprowadz dokladna analize CV i wymaган klienta.\n\n"
        
        prompt += "Wygeneruj szczegolowy raport w formacie JSON PO POLSKU:\n"
        prompt += '{\n'
        prompt += '  "podstawowe_dane": {"imie_nazwisko": "", "email": "", "telefon": ""},\n'
        prompt += '  "lokalizacja_i_dostepnosc": {\n'
        prompt += '    "lokalizacja": "miasto, kraj lub nieokreslona w CV",\n'
        prompt += '    "preferencja_pracy_zdalnej": "zdalna/hybrydowa/stacjonarna/elastyczna lub nieokreslona w CV",\n'
        prompt += '    "dostepnosc": "od kiedy dostepny lub nieokreslona w CV"\n'
        prompt += '  },\n'
        prompt += '  "krotki_opis_kandydata": "2-3 zdania podsumowujace profil, specjalizacje i kluczowe osiagniecia",\n'
        prompt += '  "stack_technologiczny": {\n'
        prompt += '    "jezyki_programowania": ["lista"],\n'
        prompt += '    "frameworki": ["lista"],\n'
        prompt += '    "bazy_danych": ["lista"],\n'
        prompt += '    "narzedzia": ["lista"],\n'
        prompt += '    "inne_technologie": ["lista"]\n'
        prompt += '  },\n'
        prompt += '  "doswiadczenie_zawodowe": [\n'
        prompt += '    {\n'
        prompt += '      "nazwa_firmy": "",\n'
        prompt += '      "stanowisko": "",\n'
        prompt += '      "daty": "MM/RRRR - MM/RRRR",\n'
        prompt += '      "opis_projektu": "opis projektow i obszarow odpowiedzialnosci",\n'
        prompt += '      "zadania": ["konkretne zadania i osiagniecia z metrykami jesli dostepne"],\n'
        prompt += '      "stos_technologiczny": ["technologie"]\n'
        prompt += '    }\n'
        prompt += '  ],\n'
        prompt += '  "edukacja": [{"uczelnia": "", "kierunek": "", "stopien": "", "daty": ""}],\n'
        prompt += '  "certyfikaty": [{"nazwa": "", "wystawca": "", "data": ""}],\n'
        prompt += '  "znajomosc_jezykow": [{"jezyk": "", "poziom": "A1/A2/B1/B2/C1/C2/native"}],\n'
        prompt += '  "dopasowanie_do_wymagan": {\n'
        prompt += '    "mocne_strony": [\n'
        prompt += '      "Minimum 5-7 punktow opisujacych kluczowe mocne strony kandydata:",\n'
        prompt += '      "- Umiejetnosci techniczne (np. ekspertyza w Python, ML, frameworki)",\n'
        prompt += '      "- Konkretne osiagniecia zawodowe z metrykami jesli sa dostepne",\n'
        prompt += '      "- Doswiadczenie w zarzadzaniu projektami lub zespolami",\n'
        prompt += '      "- Unikalny wplyw i rezultaty biznesowe",\n'
        prompt += '      "- Umiejetnosci miekkie (komunikacja, praca zespolowa, inicjatywa)",\n'
        prompt += '      "- Specjalistyczna wiedza lub niszowe kompetencje"\n'
        prompt += '    ],\n'
        prompt += '    "mapowanie_wymagan": [\n'
        prompt += '      {\n'
        prompt += '        "wymaganie": "Konkretne wymaganie z listy klienta",\n'
        prompt += '        "status": "spelnione/czesciowo spelnione/niespelnione",\n'
        prompt += '        "dowod_z_cv": "Konkretny fragment lub fakt z CV potwierdzajacy",\n'
        prompt += '        "poziom_pewnosci": "wysoki/sredni/niski",\n'
        prompt += '        "komentarz": "Dodatkowy komentarz lub kontekst"\n'
        prompt += '      }\n'
        prompt += '    ],\n'
        prompt += '    "analiza_jakosciowa": {\n'
        prompt += '      "zlozona_projektow": "wysoki/sredni/niski - ocena trudnosci i wplywu projektow",\n'
        prompt += '      "przywodztwo": "wysoki/sredni/niski - czy kandydat wykazywal inicjatywe i przywodztwo",\n'
        prompt += '      "transferowalnosc_umiejetnosci": "wysoki/sredni/niski - jak dobrze doswiadczenie pasuje do wymaган"\n'
        prompt += '    },\n'
        prompt += '    "poziom_dopasowania": "wysoki/sredni/niski",\n'
        prompt += '    "uzasadnienie": "Szczegolowe uzasadnienie oceny dopasowania (3-5 zdan) z odnieseniem do konkretnych wymagan i mocnych stron",\n'
        prompt += '    "rekomendacja": "TAK/NIE",\n'
        prompt += '    "kluczowe_czynniki": [\n'
        prompt += '      "Lista 3-5 najwazniejszych czynnikow wplywajacych na decyzje"\n'
        prompt += '    ]\n'
        prompt += '  }\n'
        prompt += '}\n\n'
        
        prompt += "WAZNE ZASADY:\n"
        prompt += "1. Wszystkie teksty MUSZA byc po polsku!\n"
        prompt += "2. Dla mocnych stron - podaj minimum 5-7 konkretnych, wartosciowych punktow\n"
        prompt += "3. W mapowaniu wymagan - przeanalizuj KAZDE wymaganie klienta osobno\n"
        prompt += "4. W dowodach z CV - cytuj konkretne fakty, nie ogolniki\n"
        prompt += "5. Uzasadnienie powinno byc szczegolowe i odnosic sie do konkretnych wymagan\n"
        prompt += "6. Jesli czegos nie ma w CV, napisz 'nieokreslona w CV'\n"
        prompt += "7. Odpowiedz MUSI byc poprawnym JSON\n"
        
        return prompt

    
    def _create_english_prompt(self, cv_text, client_requirements, needs_translation=False, source_lang='english'):
        """Prompt for English output with enhanced candidate strengths analysis"""
        prompt = "You are an HR expert specializing in CV analysis and candidate-requirement matching.\n\n"
        
        if needs_translation:
            prompt += f"IMPORTANT: The CV is written in {self._get_language_name(source_lang, 'en')}. "
            prompt += "Analyze it and generate a report IN ENGLISH, translating all information.\n\n"
        
        prompt += "CANDIDATE CV CONTENT:\n" + cv_text + "\n\n"
        prompt += "CLIENT REQUIREMENTS:\n" + client_requirements + "\n\n"
        
        prompt += "TASK: Perform a thorough analysis of the CV against client requirements.\n\n"
        
        prompt += "Generate a detailed report in JSON format IN ENGLISH:\n"
        prompt += '{\n'
        prompt += '  "podstawowe_dane": {"imie_nazwisko": "", "email": "", "telefon": ""},\n'
        prompt += '  "lokalizacja_i_dostepnosc": {\n'
        prompt += '    "lokalizacja": "city, country or not specified in CV",\n'
        prompt += '    "preferencja_pracy_zdalnej": "remote/hybrid/onsite/flexible or not specified in CV",\n'
        prompt += '    "dostepnosc": "availability date or not specified in CV"\n'
        prompt += '  },\n'
        prompt += '  "krotki_opis_kandydata": "2-3 sentences summarizing profile, specializations and key achievements",\n'
        prompt += '  "stack_technologiczny": {\n'
        prompt += '    "jezyki_programowania": ["list"],\n'
        prompt += '    "frameworki": ["list"],\n'
        prompt += '    "bazy_danych": ["list"],\n'
        prompt += '    "narzedzia": ["list"],\n'
        prompt += '    "inne_technologie": ["list"]\n'
        prompt += '  },\n'
        prompt += '  "doswiadczenie_zawodowe": [\n'
        prompt += '    {\n'
        prompt += '      "nazwa_firmy": "",\n'
        prompt += '      "stanowisko": "",\n'
        prompt += '      "daty": "MM/YYYY - MM/YYYY",\n'
        prompt += '      "opis_projektu": "description of projects and areas of responsibility",\n'
        prompt += '      "zadania": ["specific tasks and achievements with metrics if available"],\n'
        prompt += '      "stos_technologiczny": ["technologies"]\n'
        prompt += '    }\n'
        prompt += '  ],\n'
        prompt += '  "edukacja": [{"uczelnia": "", "kierunek": "", "stopien": "", "daty": ""}],\n'
        prompt += '  "certyfikaty": [{"nazwa": "", "wystawca": "", "data": ""}],\n'
        prompt += '  "znajomosc_jezykow": [{"jezyk": "", "poziom": "A1/A2/B1/B2/C1/C2/native"}],\n'
        prompt += '  "dopasowanie_do_wymagan": {\n'
        prompt += '    "mocne_strony": [\n'
        prompt += '      "Minimum 5-7 points describing key candidate strengths:",\n'
        prompt += '      "- Technical skills (e.g., Python expertise, ML, frameworks)",\n'
        prompt += '      "- Concrete professional achievements with metrics if available",\n'
        prompt += '      "- Project or team management experience",\n'
        prompt += '      "- Unique impact and business results",\n'
        prompt += '      "- Soft skills (communication, teamwork, initiative)",\n'
        prompt += '      "- Specialized knowledge or niche competencies"\n'
        prompt += '    ],\n'
        prompt += '    "mapowanie_wymagan": [\n'
        prompt += '      {\n'
        prompt += '        "wymaganie": "Specific requirement from client list",\n'
        prompt += '        "status": "met/partially met/not met",\n'
        prompt += '        "dowod_z_cv": "Specific evidence from CV confirming this",\n'
        prompt += '        "poziom_pewnosci": "high/medium/low",\n'
        prompt += '        "komentarz": "Additional comment or context"\n'
        prompt += '      }\n'
        prompt += '    ],\n'
        prompt += '    "analiza_jakosciowa": {\n'
        prompt += '      "zlozona_projektow": "high/medium/low - assessment of project difficulty and impact",\n'
        prompt += '      "przywodztwo": "high/medium/low - leadership and initiative shown",\n'
        prompt += '      "transferowalnosc_umiejetnosci": "high/medium/low - how well experience matches requirements"\n'
        prompt += '    },\n'
        prompt += '    "poziom_dopasowania": "high/medium/low",\n'
        prompt += '    "uzasadnienie": "Detailed justification of fit assessment (3-5 sentences) referencing specific requirements and strengths",\n'
        prompt += '    "rekomendacja": "YES/NO",\n'
        prompt += '    "kluczowe_czynniki": [\n'
        prompt += '      "List of 3-5 most important factors influencing the decision"\n'
        prompt += '    ]\n'
        prompt += '  }\n'
        prompt += '}\n\n'
        
        prompt += "IMPORTANT RULES:\n"
        prompt += "1. All text MUST be in English!\n"
        prompt += "2. For strengths - provide minimum 5-7 specific, valuable points\n"
        prompt += "3. In requirement mapping - analyze EACH client requirement separately\n"
        prompt += "4. In CV evidence - cite specific facts, not generalities\n"
        prompt += "5. Justification should be detailed and reference specific requirements\n"
        prompt += "6. If something is missing from CV, write 'not specified in CV'\n"
        prompt += "7. Response MUST be valid JSON\n"
        
        return prompt

    def _get_language_name(self, lang_code, output_lang):
        """Get language name in specified language"""
        names = {
            'polish': {'pl': 'polsku', 'en': 'Polish'},
            'english': {'pl': 'angielsku', 'en': 'English'}
        }
        return names.get(lang_code, {}).get(output_lang, lang_code)
    
    def generate_pdf_output(self, analysis, template_type='full'):
        """Generate PDF with proper Polish character support and template filtering"""
        # Apply template filter first
        filtered_analysis = self.apply_template_filters(analysis, template_type)
              
        buffer = BytesIO()
        
        # Try to register Unicode font
        try:
            pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))
            font_name = 'DejaVuSans'
            font_bold = 'DejaVuSans-Bold'
        except:
            # Fallback to Courier which has better UTF-8 support than Times
            font_name = 'Courier'
            font_bold = 'Courier-Bold'
        
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        
        styles = getSampleStyleSheet()
        
        # Custom styles with Unicode font
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1f77b4'),
            fontName=font_bold,
            alignment=1,
            spaceAfter=20
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#2c3e50'),
            fontName=font_bold,
            spaceAfter=8,
            spaceBefore=10
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=9,
            fontName=font_name,
            spaceAfter=5,
            leading=12
        )
        
        bold_style = ParagraphStyle(
            'CustomBold',
            parent=styles['Normal'],
            fontSize=9,
            fontName=font_bold,
            leading=12
        )
        
        story = []
        
        # Determine output language
        output_lang = filtered_analysis.get('output_language', 'english')
        is_polish = (output_lang == 'polish')
        
        # Helper to safely encode text for PDF
        def safe_text(text):
            if text is None:
                return 'N/A'
            text = str(text)
            # Escape XML special characters
            text = text.replace('&', '&amp;')
            text = text.replace('<', '&lt;')
            text = text.replace('>', '&gt;')
            # Ensure proper Unicode encoding
            try:
                text.encode('utf-8')
                return text
            except:
                return text.encode('utf-8', errors='ignore').decode('utf-8')
        
        # Headers dictionary
        h = {
            'title': 'Profil Kandydata' if is_polish else 'Candidate Profile',
            'detected': 'Wykryty język' if is_polish else 'Detected Language',
            'basic': 'INFORMACJE PODSTAWOWE' if is_polish else 'BASIC INFORMATION',
            'location': 'LOKALIZACJA I DOSTĘPNOŚĆ' if is_polish else 'LOCATION AND AVAILABILITY',
            'summary': 'KRÓTKI OPIS KANDYDATA' if is_polish else 'CANDIDATE SUMMARY',
            'tech': 'STACK TECHNOLOGICZNY' if is_polish else 'TECHNOLOGY STACK',
            'experience': 'DOŚWIADCZENIE ZAWODOWE' if is_polish else 'WORK EXPERIENCE',
            'education': 'EDUKACJA' if is_polish else 'EDUCATION',
            'certificates': 'CERTYFIKATY' if is_polish else 'CERTIFICATES',
            'languages': 'ZNAJOMOŚĆ JĘZYKÓW' if is_polish else 'LANGUAGES',
            'fit': 'DOPASOWANIE DO WYMAGAŃ' if is_polish else 'FIT ASSESSMENT',
            'name': 'Imię i nazwisko' if is_polish else 'Name',
            'email': 'Email',
            'phone': 'Telefon' if is_polish else 'Phone',
            'loc': 'Lokalizacja' if is_polish else 'Location',
            'remote': 'Praca zdalna' if is_polish else 'Remote Work',
            'avail': 'Dostępność' if is_polish else 'Availability',
            'prog_lang': 'Języki programowania' if is_polish else 'Programming Languages',
            'frameworks': 'Frameworki' if is_polish else 'Frameworks',
            'databases': 'Bazy danych' if is_polish else 'Databases',
            'tools': 'Narzędzia' if is_polish else 'Tools',
            'position': 'Stanowisko' if is_polish else 'Position',
            'period': 'Okres' if is_polish else 'Period',
            'project': 'Projekt' if is_polish else 'Project',
            'tasks': 'Zadania' if is_polish else 'Tasks',
            'match': 'POZIOM DOPASOWANIA' if is_polish else 'MATCH LEVEL',
            'recommendation': 'REKOMENDACJA' if is_polish else 'RECOMMENDATION',
            'justification': 'Uzasadnienie' if is_polish else 'Justification',
            'strengths': 'Mocne strony' if is_polish else 'Key Strengths'
        }
        
        # Build PDF content
        story.append(Paragraph(safe_text(h['title']), title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Add anonymous watermark if applicable
        if template_type == 'anonymous':
            warning_text = '⚠️ RAPORT ANONIMOWY - DANE OSOBOWE UKRYTE' if is_polish else '⚠️ ANONYMOUS REPORT - PERSONAL DATA HIDDEN'
            story.append(Paragraph(f"<i>{safe_text(warning_text)}</i>", normal_style))
            story.append(Spacer(1, 0.15*inch))
        
        if "detected_language" in filtered_analysis:
            story.append(Paragraph(f"<b>{safe_text(h['detected'])}:</b> {safe_text(filtered_analysis['detected_language'].upper())}", normal_style))
            story.append(Spacer(1, 0.15*inch))
        
        if "podstawowe_dane" in filtered_analysis:
            dane = filtered_analysis["podstawowe_dane"]
            story.append(Paragraph(safe_text(h['basic']), heading_style))
            story.append(Paragraph(f"<b>{safe_text(h['name'])}:</b> {safe_text(dane.get('imie_nazwisko', 'N/A'))}", normal_style))
            story.append(Paragraph(f"<b>{safe_text(h['email'])}:</b> {safe_text(dane.get('email', 'N/A'))}", normal_style))
            story.append(Paragraph(f"<b>{safe_text(h['phone'])}:</b> {safe_text(dane.get('telefon', 'N/A'))}", normal_style))
            story.append(Spacer(1, 0.15*inch))
        
        if "lokalizacja_i_dostepnosc" in filtered_analysis:
            lok = filtered_analysis["lokalizacja_i_dostepnosc"]
            story.append(Paragraph(safe_text(h['location']), heading_style))
            story.append(Paragraph(f"<b>{safe_text(h['loc'])}:</b> {safe_text(lok.get('lokalizacja', 'N/A'))}", normal_style))
            story.append(Paragraph(f"<b>{safe_text(h['remote'])}:</b> {safe_text(lok.get('preferencja_pracy_zdalnej', 'N/A'))}", normal_style))
            story.append(Paragraph(f"<b>{safe_text(h['avail'])}:</b> {safe_text(lok.get('dostepnosc', 'N/A'))}", normal_style))
            story.append(Spacer(1, 0.15*inch))
        
        if "krotki_opis_kandydata" in filtered_analysis:
            story.append(Paragraph(safe_text(h['summary']), heading_style))
            story.append(Paragraph(safe_text(filtered_analysis["krotki_opis_kandydata"]), normal_style))
            story.append(Spacer(1, 0.15*inch))
        
        if "stack_technologiczny" in filtered_analysis:
            stack = filtered_analysis["stack_technologiczny"]
            story.append(Paragraph(safe_text(h['tech']), heading_style))
            
            if stack.get('jezyki_programowania'):
                langs = ', '.join([safe_text(x) for x in stack['jezyki_programowania']])
                story.append(Paragraph(f"<b>{safe_text(h['prog_lang'])}:</b> {langs}", normal_style))
            if stack.get('frameworki'):
                fws = ', '.join([safe_text(x) for x in stack['frameworki']])
                story.append(Paragraph(f"<b>{safe_text(h['frameworks'])}:</b> {fws}", normal_style))
            if stack.get('bazy_danych'):
                dbs = ', '.join([safe_text(x) for x in stack['bazy_danych']])
                story.append(Paragraph(f"<b>{safe_text(h['databases'])}:</b> {dbs}", normal_style))
            if stack.get('narzedzia'):
                tools = ', '.join([safe_text(x) for x in stack['narzedzia']])
                story.append(Paragraph(f"<b>{safe_text(h['tools'])}:</b> {tools}", normal_style))
            
            story.append(Spacer(1, 0.15*inch))
        
        if "doswiadczenie_zawodowe" in filtered_analysis and filtered_analysis["doswiadczenie_zawodowe"]:
            story.append(Paragraph(safe_text(h['experience']), heading_style))
            
            for idx, exp in enumerate(filtered_analysis["doswiadczenie_zawodowe"], 1):
                story.append(Paragraph(f"<b>{idx}. {safe_text(exp.get('nazwa_firmy', 'N/A'))}</b>", bold_style))
                story.append(Paragraph(f"<b>{safe_text(h['position'])}:</b> {safe_text(exp.get('stanowisko', 'N/A'))}", normal_style))
                story.append(Paragraph(f"<b>{safe_text(h['period'])}:</b> {safe_text(exp.get('daty', 'N/A'))}", normal_style))
                story.append(Paragraph(f"<b>{safe_text(h['project'])}:</b> {safe_text(exp.get('opis_projektu', 'N/A'))}", normal_style))
                
                if exp.get('zadania'):
                    story.append(Paragraph(f"<b>{safe_text(h['tasks'])}:</b>", bold_style))
                    for zadanie in exp['zadania']:
                        story.append(Paragraph(f"• {safe_text(zadanie)}", normal_style))
                
                story.append(Spacer(1, 0.1*inch))
            
            story.append(Spacer(1, 0.15*inch))
        
        if "edukacja" in filtered_analysis and filtered_analysis["edukacja"]:
            story.append(Paragraph(safe_text(h['education']), heading_style))
            for edu in filtered_analysis["edukacja"]:
                if edu.get('uczelnia') or edu.get('kierunek'):
                    story.append(Paragraph(f"<b>{safe_text(edu.get('stopien', ''))} - {safe_text(edu.get('kierunek', 'N/A'))}</b>", normal_style))
                    story.append(Paragraph(f"{safe_text(edu.get('uczelnia', 'N/A'))} ({safe_text(edu.get('daty', 'N/A'))})", normal_style))
            story.append(Spacer(1, 0.15*inch))
        
        if "certyfikaty" in filtered_analysis and filtered_analysis["certyfikaty"]:
            story.append(Paragraph(safe_text(h['certificates']), heading_style))
            for cert in filtered_analysis["certyfikaty"]:
                if cert.get('nazwa'):
                    story.append(Paragraph(f"• {safe_text(cert['nazwa'])} - {safe_text(cert.get('wystawca', 'N/A'))} ({safe_text(cert.get('data', 'N/A'))})", normal_style))
            story.append(Spacer(1, 0.15*inch))
        
        if "znajomosc_jezykow" in filtered_analysis and filtered_analysis["znajomosc_jezykow"]:
            story.append(Paragraph(safe_text(h['languages']), heading_style))
            for lang in filtered_analysis["znajomosc_jezykow"]:
                if lang.get('jezyk'):
                    story.append(Paragraph(f"• {safe_text(lang['jezyk'])}: {safe_text(lang.get('poziom', 'N/A'))}", normal_style))
            story.append(Spacer(1, 0.15*inch))
        
        if "dopasowanie_do_wymagan" in filtered_analysis:
            dop = filtered_analysis["dopasowanie_do_wymagan"]
            
            story.append(Paragraph(safe_text(h['fit']), heading_style))
            story.append(Spacer(1, 0.1*inch))
            
            match_level = safe_text(dop.get('poziom_dopasowania', 'N/A')).upper()
            recommendation = safe_text(dop.get('rekomendacja', 'N/A')).upper()
            
            data = [
                [Paragraph(f"<b>{safe_text(h['match'])}:</b>", bold_style), 
                Paragraph(f"<b>{match_level}</b>", bold_style)],
                [Paragraph(f"<b>{safe_text(h['recommendation'])}:</b>", bold_style), 
                Paragraph(f"<b>{recommendation}</b>", bold_style)]
            ]
            
            t = Table(data, colWidths=[3*inch, 2.5*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8f4f8')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), font_bold),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
            ]))
            story.append(t)
            story.append(Spacer(1, 0.15*inch))
            
            if dop.get('uzasadnienie'):
                story.append(Paragraph(f"<b>{safe_text(h['justification'])}:</b>", bold_style))
                story.append(Paragraph(safe_text(dop['uzasadnienie']), normal_style))
                story.append(Spacer(1, 0.15*inch))
            
            if dop.get('mocne_strony'):
                story.append(Paragraph(f"<b>{safe_text(h['strengths'])}:</b>", bold_style))
                for idx, strength in enumerate(dop['mocne_strony'], 1):
                    story.append(Paragraph(f"{idx}. {safe_text(strength)}", normal_style))
        
        doc.build(story)
        buffer.seek(0)
        return buffer

    
    def generate_docx_output(self, analysis, template_type='full'):
        """Generate comprehensive DOCX output from analysis with template support"""
        # Apply template filter first
        filtered_analysis = self.apply_template_filters(analysis, template_type)
        
        doc = Document()
        
        # Determine output language
        output_lang = filtered_analysis.get('output_language', 'english')
        is_polish = (output_lang == 'polish')
        
        # Translations for headers
        headers = {
            'title': 'Profil Kandydata' if is_polish else 'Candidate Profile',
            'detected': 'Wykryty język' if is_polish else 'Detected Language',
            'basic': 'INFORMACJE PODSTAWOWE' if is_polish else 'BASIC INFORMATION',
            'location': 'LOKALIZACJA I DOSTĘPNOŚĆ' if is_polish else 'LOCATION & AVAILABILITY',
            'summary': 'KRÓTKI OPIS KANDYDATA' if is_polish else 'CANDIDATE SUMMARY',
            'tech': 'STACK TECHNOLOGICZNY' if is_polish else 'TECHNOLOGY STACK',
            'experience': 'DOŚWIADCZENIE ZAWODOWE' if is_polish else 'WORK EXPERIENCE',
            'education': 'EDUKACJA' if is_polish else 'EDUCATION',
            'certificates': 'CERTYFIKATY' if is_polish else 'CERTIFICATES',
            'languages': 'ZNAJOMOŚĆ JĘZYKÓW' if is_polish else 'LANGUAGES',
            'fit': 'DOPASOWANIE DO WYMAGAŃ' if is_polish else 'FIT ASSESSMENT',
            'name': 'Imię i nazwisko' if is_polish else 'Name',
            'email': 'Email',
            'phone': 'Telefon' if is_polish else 'Phone',
            'loc': 'Lokalizacja' if is_polish else 'Location',
            'remote': 'Preferencja pracy zdalnej' if is_polish else 'Remote Work Preference',
            'avail': 'Dostępność' if is_polish else 'Availability',
            'prog_lang': 'Języki programowania' if is_polish else 'Programming Languages',
            'frameworks': 'Frameworki' if is_polish else 'Frameworks',
            'databases': 'Bazy danych' if is_polish else 'Databases',
            'tools': 'Narzędzia i technologie' if is_polish else 'Tools & Technologies',
            'other': 'Inne technologie' if is_polish else 'Other Technologies',
            'position': 'Stanowisko' if is_polish else 'Position',
            'period': 'Okres' if is_polish else 'Period',
            'project': 'Opis projektu' if is_polish else 'Project Description',
            'tasks': 'Kluczowe zadania i odpowiedzialności' if is_polish else 'Key Responsibilities & Tasks',
            'tech_stack': 'Stack technologiczny' if is_polish else 'Tech Stack',
            'degree': 'Stopień' if is_polish else 'Degree',
            'in': 'w dziedzinie' if is_polish else 'in',
            'match': 'POZIOM DOPASOWANIA' if is_polish else 'MATCH LEVEL',
            'recommendation': 'REKOMENDACJA' if is_polish else 'RECOMMENDATION',
            'justification': 'Uzasadnienie' if is_polish else 'Justification',
            'strengths': 'Mocne Strony' if is_polish else 'Key Strengths'
        }
        
        # Title
        title = doc.add_heading(headers['title'], 0)
        title.alignment = 1  # Center
        
        # Add anonymous watermark if applicable
        if template_type == 'anonymous':
            p = doc.add_paragraph()
            run = p.add_run('⚠️ RAPORT ANONIMOWY - DANE OSOBOWE UKRYTE' if is_polish else '⚠️ ANONYMOUS REPORT - PERSONAL DATA HIDDEN')
            run.italic = True
            run.font.size = 152400  # 12pt
        
        # Detected Language
        if "detected_language" in filtered_analysis:
            p = doc.add_paragraph()
            p.add_run(f"{headers['detected']}: {filtered_analysis['detected_language'].upper()}").bold = True
        
        # Basic Info
        if "podstawowe_dane" in filtered_analysis:
            dane = filtered_analysis["podstawowe_dane"]
            doc.add_heading(headers['basic'], level=1)
            doc.add_paragraph(f"{headers['name']}: {dane.get('imie_nazwisko', 'N/A')}")
            doc.add_paragraph(f"{headers['email']}: {dane.get('email', 'N/A')}")
            doc.add_paragraph(f"{headers['phone']}: {dane.get('telefon', 'N/A')}")
        
        # Location & Availability
        if "lokalizacja_i_dostepnosc" in filtered_analysis:
            lok = filtered_analysis["lokalizacja_i_dostepnosc"]
            doc.add_heading(headers['location'], level=1)
            doc.add_paragraph(f"{headers['loc']}: {lok.get('lokalizacja', 'N/A')}")
            doc.add_paragraph(f"{headers['remote']}: {lok.get('preferencja_pracy_zdalnej', 'N/A')}")
            doc.add_paragraph(f"{headers['avail']}: {lok.get('dostepnosc', 'N/A')}")
        
        # Summary
        if "krotki_opis_kandydata" in filtered_analysis:
            doc.add_heading(headers['summary'], level=1)
            doc.add_paragraph(str(filtered_analysis["krotki_opis_kandydata"]))
        
        # Tech Stack
        if "stack_technologiczny" in filtered_analysis:
            stack = filtered_analysis["stack_technologiczny"]
            doc.add_heading(headers['tech'], level=1)
            
            if stack.get('jezyki_programowania'):
                doc.add_paragraph(f"{headers['prog_lang']}: {', '.join(stack.get('jezyki_programowania', []))}")
            if stack.get('frameworki'):
                doc.add_paragraph(f"{headers['frameworks']}: {', '.join(stack.get('frameworki', []))}")
            if stack.get('bazy_danych'):
                doc.add_paragraph(f"{headers['databases']}: {', '.join(stack.get('bazy_danych', []))}")
            if stack.get('narzedzia'):
                doc.add_paragraph(f"{headers['tools']}: {', '.join(stack.get('narzedzia', []))}")
            if stack.get('inne_technologie'):
                doc.add_paragraph(f"{headers['other']}: {', '.join(stack.get('inne_technologie', []))}")
        
        # Work Experience
        if "doswiadczenie_zawodowe" in filtered_analysis and filtered_analysis["doswiadczenie_zawodowe"]:
            doc.add_heading(headers['experience'], level=1)
            
            for idx, exp in enumerate(filtered_analysis["doswiadczenie_zawodowe"], 1):
                doc.add_heading(f"{idx}. {exp.get('nazwa_firmy', 'N/A')}", level=2)
                doc.add_paragraph(f"{headers['position']}: {exp.get('stanowisko', 'N/A')}")
                doc.add_paragraph(f"{headers['period']}: {exp.get('daty', 'N/A')}")
                doc.add_paragraph(f"{headers['project']}: {exp.get('opis_projektu', 'N/A')}")
                
                if exp.get('zadania'):
                    p = doc.add_paragraph(headers['tasks'] + ':')
                    p.runs[0].bold = True
                    for zadanie in exp.get('zadania', []):
                        doc.add_paragraph(zadanie, style='List Bullet')
                
                if exp.get('stos_technologiczny'):
                    doc.add_paragraph(f"{headers['tech_stack']}: {', '.join(exp.get('stos_technologiczny', []))}")
        
        # Education
        if "edukacja" in filtered_analysis and filtered_analysis["edukacja"]:
            doc.add_heading(headers['education'], level=1)
            for edu in filtered_analysis["edukacja"]:
                if edu.get('uczelnia') or edu.get('kierunek'):
                    p = doc.add_paragraph(f"{edu.get('stopien', '')} {headers['in']} {edu.get('kierunek', 'N/A')}")
                    p.runs[0].bold = True
                    doc.add_paragraph(f"{edu.get('uczelnia', 'N/A')} ({edu.get('daty', 'N/A')})")
        
        # Certificates
        if "certyfikaty" in filtered_analysis and filtered_analysis["certyfikaty"]:
            doc.add_heading(headers['certificates'], level=1)
            for cert in filtered_analysis["certyfikaty"]:
                if cert.get('nazwa'):
                    doc.add_paragraph(f"{cert.get('nazwa', '')} - {cert.get('wystawca', 'N/A')} ({cert.get('data', 'N/A')})", style='List Bullet')
        
        # Languages
        if "znajomosc_jezykow" in filtered_analysis and filtered_analysis["znajomosc_jezykow"]:
            doc.add_heading(headers['languages'], level=1)
            for lang in filtered_analysis["znajomosc_jezykow"]:
                if lang.get('jezyk'):
                    doc.add_paragraph(f"{lang.get('jezyk', '')}: {lang.get('poziom', 'N/A')}", style='List Bullet')
        
        # FIT ASSESSMENT
        if "dopasowanie_do_wymagan" in filtered_analysis:
            dop = filtered_analysis["dopasowanie_do_wymagan"]
            
            doc.add_heading(headers['fit'], level=1)
            
            # Match Level
            p = doc.add_paragraph()
            p.add_run(headers['match'] + ': ').bold = True
            run = p.add_run(str(dop.get('poziom_dopasowania', 'N/A')).upper())
            run.bold = True
            run.font.size = 177800  # 14pt
            
            # Recommendation
            p = doc.add_paragraph()
            p.add_run(headers['recommendation'] + ': ').bold = True
            run = p.add_run(str(dop.get('rekomendacja', 'N/A')).upper())
            run.bold = True
            run.font.size = 177800  # 14pt
            
            # Justification
            if dop.get('uzasadnienie'):
                doc.add_paragraph()
                p = doc.add_paragraph()
                p.add_run(headers['justification'] + ':').bold = True
                doc.add_paragraph(str(dop.get('uzasadnienie', 'N/A')))
            
            # Key Strengths
            if dop.get('mocne_strony'):
                doc.add_paragraph()
                p = doc.add_paragraph()
                p.add_run(headers['strengths'] + ':').bold = True
                for idx, strength in enumerate(dop.get('mocne_strony', []), 1):
                    doc.add_paragraph(f"{idx}. {strength}", style='List Number')
        
        # Extended recommendations (only for extended template)
        if template_type == 'extended' and "dopasowanie_do_wymagan" in filtered_analysis:
            if 'extended_recommendations' in filtered_analysis["dopasowanie_do_wymagan"]:
                ext = filtered_analysis["dopasowanie_do_wymagan"]['extended_recommendations']
                
                doc.add_heading('ROZSZERZONE REKOMENDACJE' if is_polish else 'EXTENDED RECOMMENDATIONS', level=1)
                
                if 'interview_questions' in ext:
                    doc.add_heading('Pytania rekrutacyjne' if is_polish else 'Interview Questions', level=2)
                    for q in ext['interview_questions']:
                        doc.add_paragraph(q, style='List Bullet')
                
                if 'development_areas' in ext:
                    doc.add_heading('Obszary rozwoju' if is_polish else 'Development Areas', level=2)
                    for area in ext['development_areas']:
                        doc.add_paragraph(area, style='List Bullet')
        
        # Save to BytesIO
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer


