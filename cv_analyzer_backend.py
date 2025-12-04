import pymupdf
from PIL import Image
import pytesseract
import ollama
import json
import os
import re

from docx.oxml import parse_xml
from fpdf import FPDF

from PIL import ImageEnhance, ImageFilter, Image
import numpy as np
from io import BytesIO
from reportlab.platypus import Paragraph, Spacer

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from reportlab.lib.pagesizes import A4

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# Dla Windows odkomentuj:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


from ollama import Client
ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
ollama_client = Client(host=ollama_host)

try:
    # Próba użycia systemowych fontów
    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))
except:
    # Jeśli nie ma DejaVu, użyj domyślnych z ReportLab
    from reportlab.lib.fonts import addMapping
    # ReportLab ma wbudowane fonty z podstawowym wsparciem UTF-8


def try_fill_company_period_from_text(section, job):
    """
    Uzupełnia company/period na podstawie surowego tekstu sekcji/całego CV.
    Obsługuje układ:
        <job title>
        <firmy | ... | daty>
    oraz:
        <job title> - <firma>, <daty>
    """
    if job.get("company") and job.get("period"):
        return job

    position = (job.get("position") or "").strip()
    if not position:
        return job

    lines = section.splitlines()

    for idx, line in enumerate(lines):
        if position.lower() in line.lower():
            candidate_lines = [line]
            if idx + 1 < len(lines):
                candidate_lines.append(lines[idx + 1])

            combined = " ".join(candidate_lines)

            # okres
            m_period = re.search(
                r"(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
                r"\s+\d{4}\s*[-–]\s*(?:current|present|"
                r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}))",
                combined,
                re.IGNORECASE,
            )
            if m_period and not job.get("period"):
                job["period"] = m_period.group(1).strip()

            # firma = wszystko przed okresem (albo cała linia, jeśli dat brak)
            if m_period:
                before_period = combined[:m_period.start()].strip()
            else:
                before_period = combined.strip()

            if before_period and not job.get("company"):
                # wytnij sam tytuł stanowiska
                low = before_period.lower()
                pos_low = position.lower()
                if pos_low in low:
                    start = low.find(pos_low)
                    before_period = before_period[start + len(position):].strip(" -–|,")
                if len(before_period) > 2:
                    job["company"] = before_period

            break

    return job


def safe_text(text, default="NA"):
    if text is None or text == "":
        return default
    if isinstance(text, list):  # ✅ OBSŁUGA LIST
        return ", ".join([str(x) for x in text if x])
    return str(text).strip()

class CVAnalyzer:
    def __init__(self, model_name="qwen2.5:14b"):
        self.model_name = model_name
        
        self.TECH_KNOWLEDGE_BASE = {
            "programming": [
                "Python", "Java", "C#", "JavaScript", "TypeScript", "C++", "Go", "Ruby", "PHP", 
                "Swift", "Kotlin", "Rust", "C", "Scala", "R", "MATLAB", "Julia", "Bash", "PowerShell",
                "Perl", "Haskell", "Erlang", "Elixir", "Clojure", "Groovy", "VB.NET", "F#",
                "Objective-C", "Dart", "Lua", "Coffeescript", "Assembly", "VBA"
            ],
            "frameworks": [
                "Django", "Flask", "FastAPI", "Spring", "Spring Boot", "Express", "NestJS", "Fastify",
                "React", "Angular", "Vue", "Svelte", "Next.js", "Remix", "SvelteKit",
                "PyTorch", "TensorFlow", "Keras", "JAX", "Scikit-learn", "Pandas", "NumPy",
                "Polars", "H2O.ai", "XGBoost", "LightGBM", "CatBoost",
                "Rails", "Laravel", "Symfony", "Django REST", "GraphQL",
                "Pytest", "Jest", "Mocha", "Jasmine", "JUnit", "TestNG", "Mockito",
                "Selenium", "Cypress", "Playwright", "RxJava", "Coroutines", "Compose", "Jetpack",
                "Hibernate", "JPA", "Sequelize", "TypeORM", "Prisma", "SQLAlchemy",
                "Maven", "Gradle", "npm", "yarn", "pip", "conda", "cargo",
                "MVVM", "MVP", "MVI", "CLEAN", "Hexagonal"
            ],
            "mobile": [
                "Android", "iOS", "React Native", "Flutter", "Kotlin", "Swift", "Objective-C",
                "Xamarin", "NativeScript", "Ionic", "PhoneGap", "Cordova",
                "Jetpack Compose", "SwiftUI", "UIKit", "AppKit",
                "Firebase", "Realm", "SQLite", "Room", "CoreData"
            ],
            "infrastructure": [
                "Docker", "Kubernetes", "Git", "GitHub", "GitLab", "Bitbucket", "Jenkins", "GitLab CI",
                "GitHub Actions", "CircleCI", "Travis CI", "Azure Pipelines",
                "Terraform", "Ansible", "Puppet", "Chef", "CloudFormation",
                "Nginx", "Apache", "IIS", "Tomcat", "JBoss",
                "Linux", "Windows", "macOS", "Ubuntu", "CentOS", "RHEL", "Alpine"
            ],
            "cloud": [
                "AWS", "EC2", "S3", "Lambda", "RDS", "DynamoDB", "SQS", "SNS", "CloudFormation",
                "Azure", "Virtual Machines", "App Service", "Blob Storage", "SQL Database",
                "Azure Functions", "Azure DevOps",
                "GCP", "Compute Engine", "Cloud Storage", "Cloud SQL", "Cloud Functions", "BigQuery"
            ],
            "databases": [
                "PostgreSQL", "MySQL", "MongoDB", "Cassandra", "Redis", "Memcached",
                "Elasticsearch", "Solr", "Neo4j", "DynamoDB", "Firestore", "MariaDB",
                "Oracle", "SQL Server", "Snowflake", "BigQuery", "Redshift", "Athena",
                "ClickHouse", "Prometheus", "InfluxDB", "TimescaleDB", "Couchbase"
            ],
            "messaging": [
                "Kafka", "RabbitMQ", "ActiveMQ", "Redis Streams", "ZeroMQ", "gRPC",
                "Apache Pulsar", "NATS", "Amazon SQS", "Amazon SNS", "Google Pub/Sub",
                "Azure Service Bus", "Azure Event Hub", "AWS Kinesis"
            ],
            "monitoring": [
                "Prometheus", "Grafana", "Datadog", "New Relic", "Splunk", "ELK Stack",
                "Elasticsearch", "Kibana", "Logstash", "Jaeger", "Zipkin", "Fluentd",
                "PagerDuty", "CloudWatch", "StackDriver", "Dynatrace", "AppDynamics",
                "Sentry", "Rollbar", "Airbrake", "Bugsnag"
            ],
            "other": [
                "Agile", "Scrum", "Kanban", "REST API", "GraphQL", "gRPC", "OAuth", "JWT", "SAML",
                "SSL", "TLS", "HTTPS", "HTTP/2", "WebSocket", "WebAssembly",
                "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "Data Science",
                "Big Data", "Hadoop", "Spark", "Hive", "Pig",
                "BDD", "TDD", "Microservices", "Monolith", "Serverless",
                "CI/CD", "DevOps", "SRE", "Observability", "Infrastructure as Code"
            ]
        }
                
    def _add_paragraph_with_bold_keywords(self, cell, text, keywords, base_size=7, bold_base=False, space_before=0, space_after=0):
        """Add paragraph to DOCX cell with BOLD keywords"""
        p = cell.add_paragraph()
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)

        
        words = str(text).split()
        for i, word in enumerate(words):
            word_lower = word.lower().strip('.,;:!?()"\'')
            has_keyword = any(kw.lower() in word_lower for kw in keywords) if keywords else False
            
            # Add word with formatting
            run = p.add_run(word)
            run.font.name = 'Arsenal'
            run.font.size = Pt(base_size)
            run.bold = (has_keyword or bold_base)
            
            # Add space after word (except last)
            if i < len(words) - 1:
                run_space = p.add_run(' ')
                run_space.font.name = 'Arsenal'
                run_space.font.size = Pt(base_size)
                run_space.bold = bold_base
        
        return p

    
    def _extract_text_from_pdf_with_ocr(self, pdf_content):
        """Extract text from PDF using OCR with improved preprocessing"""
        try:
            if hasattr(pdf_content, 'read'):
                pdf_content = pdf_content.read()

            doc = pymupdf.open(stream=pdf_content, filetype="pdf")
            all_text = ""

            for page_num, page in enumerate(doc):
                print(f"📄 OCR: page {page_num + 1}...")

                # 3x zoom instead of 2x
                mat = pymupdf.Matrix(3, 3)
                pix = page.get_pixmap(matrix=mat, alpha=False)

                # Convert to PIL Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img = img.convert('L')

                # PREPROCESSING - IMPROVED
                # 1. Contrast - 2.5x instead of 2x
                contrast = ImageEnhance.Contrast(img)
                img = contrast.enhance(2.5)

                # 2. Sharpness - NEW
                sharpness = ImageEnhance.Sharpness(img)
                img = sharpness.enhance(2.0)

                # 3. Brightness - NEW
                brightness = ImageEnhance.Brightness(img)
                img = brightness.enhance(1.1)

                # 4. Median Filter to remove noise - NEW
                img = img.filter(ImageFilter.MedianFilter(size=3))

                # 5. Thresholding - black and white for better OCR - NEW
                img_array = np.array(img)
                threshold_value = 150
                binary_array = np.where(img_array > threshold_value, 255, 0).astype(np.uint8)
                img = Image.fromarray(binary_array)

                # OCR with better parameters
                text = pytesseract.image_to_string(
                    img, 
                    lang='pol+eng',
                    config='--psm 6 --oem 3'  # PSM 6: uniform block, OEM 3: both engines
                )

                all_text += text + "\n"

            doc.close()
            return all_text

        except Exception as e:
            print(f"❌ OCR error: {e}")
            return ""   
     
    def extract_text_from_pdf(self, pdf_file):
        """Extract text from PDF file or BytesIO object - with OCR fallback for scanned PDFs"""
        try:
            if hasattr(pdf_file, 'read'):
                pdf_content = pdf_file.read()
            else:
                pdf_content = pdf_file

            doc = pymupdf.open(stream=pdf_content, filetype="pdf")
            text = ""

            # Najpierw spróbuj standardową ekstrakcję tekstu
            for page in doc:
                text += page.get_text()

            doc.close()

            # Jeśli tekst jest praktycznie pusty (<50 znaków), to prawdopodobnie skan - użyj OCR
            if len(text.strip()) < 50:
                print("⚠️ Detected scanned PDF (no selectable text), using OCR...")
                return self._extract_text_from_pdf_with_ocr(pdf_content)

            return text

        except Exception as e:
            print(f"Error reading PDF: {e}")
            # Fallback to OCR
            if 'pdf_content' in locals():
                return self._extract_text_from_pdf_with_ocr(pdf_content)
            else:
                return self._extract_text_from_pdf_with_ocr(pdf_file)
    
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
    
    def analyze_cv_for_template(self, cv_text, client_requirements, custom_prompt="", output_language="auto"):
        """
        Analyze CV and generate structured template WITHOUT using Ollama for extraction.
        Uses direct regex parsing instead.
        """
        # Detect language
        cv_language = self.detect_language(cv_text)
        
        if output_language == "auto":
            final_language = cv_language
        else:
            final_language = output_language
        
        print(f"\n🔍 Analyzing CV (detected: {cv_language}, output: {final_language})")
        
        # STEP 1: Extract work experience using direct parsing (NO OLLAMA)
        work_experience = self._extract_work_experience_details(cv_text)
        
        # STEP 2: Extract education using direct parsing (NO OLLAMA)
        education = self._extract_education_details(cv_text)
        
        # STEP 3: Extract technologies
        extracted_tech = self._extract_technologies_from_cv(cv_text)
        categorized_tech = self._categorize_technologies(extracted_tech)
        
        # STEP 4: Extract basic info using Ollama (name, email, phone only)
        basic_info_prompt = f"""Extract ONLY basic contact information from this CV:

    CV TEXT:
    {cv_text}

    Return ONLY in this format:
    Name: [Full Name]
    Email: [email or "not provided"]
    Phone: [phone or "not provided"]
    Location: [city, country or "not provided"]

    EXTRACT ONLY - DO NOT GENERATE OR ASSUME."""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': basic_info_prompt}],
                options={'temperature': 0.05, 'num_predict': 200}
            )
            basic_text = response['message']['content']
            
            # Parse basic info
            name_match = re.search(r'Name:\s*(.+)', basic_text)
            email_match = re.search(r'Email:\s*(.+)', basic_text)
            phone_match = re.search(r'Phone:\s*(.+)', basic_text)
            location_match = re.search(r'Location:\s*(.+)', basic_text)
            
            full_name = name_match.group(1).strip() if name_match else "Candidate"
            email = email_match.group(1).strip() if email_match else "not provided"
            phone = phone_match.group(1).strip() if phone_match else "not provided"
            location = location_match.group(1).strip() if location_match else "not provided"
            
        except Exception as e:
            print(f"❌ Basic info extraction error: {e}")
            full_name = "Candidate"
            email = "not provided"
            phone = "not provided"
            location = "not provided"
        
        # STEP 5: Generate profile summary using Ollama
        profile_prompt = f"""You are an HR expert. Write a professional profile summary (3-5 sentences) based on this information:

    WORK EXPERIENCE:
    {chr(10).join([f"- {job['position']} at {job['company']} ({job['period']})" for job in work_experience])}

    TECHNOLOGIES:
    {', '.join(extracted_tech[:20])}

    CLIENT REQUIREMENTS:
    {client_requirements}

    Write a concise professional summary highlighting experience, key skills, and fit for requirements.
    Write in {"Polish" if final_language == "polish" else "English"}."""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': profile_prompt}],
                options={'temperature': 0.3, 'num_predict': 300}
            )
            profile_summary = response['message']['content'].strip()
        except:
            profile_summary = f"Experienced professional with expertise in {', '.join(extracted_tech[:5])}."
        
        # STEP 6: Build final analysis dict
        analysis = {
            "detected_language": cv_language,
            "output_language": final_language
        }
        
        if final_language == "polish":
            analysis.update({
                "podstawowe_dane": {
                    "imie_nazwisko": full_name,
                    "email": email,
                    "telefon": phone
                },
                "lokalizacja_i_dostepnosc": {
                    "lokalizacja": location,
                    "preferencja_pracy_zdalnej": "nie określona",
                    "dostepnosc": "nie określona"
                },
                "podsumowanie_profilu": profile_summary,
                "doswiadczenie_zawodowe": [
                    {
                        "okres": job['period'],
                        "firma": job['company'],
                        "stanowisko": job['position'],
                        "kluczowe_osiagniecia": job['description'],
                        "obowiazki": "",
                        "technologie": job.get('technologies', [])
                    }
                    for job in work_experience
                ],
                "wyksztalcenie": [
                    {
                        "uczelnia": edu['institution'],
                        "stopien": edu['degree'],
                        "kierunek": edu['field'],
                        "okres": edu['period']
                    }
                    for edu in education
                ],
                "certyfikaty_i_kursy": [],
                "jezyki_obce": [{"jezyk": "English", "poziom": "C1"}],
                "umiejetnosci": {
                    "programowanie_skrypty": categorized_tech.get('programming_scripting', []),
                    "frameworki_biblioteki": categorized_tech.get('frameworks_libraries', []),
                    "infrastruktura_devops": categorized_tech.get('infrastructure_devops', []),
                    "chmura": categorized_tech.get('cloud', []),
                    "bazy_kolejki": categorized_tech.get('databases_messaging', []),
                    "monitoring": categorized_tech.get('monitoring', []),
                    "inne": categorized_tech.get('other', [])
                },
                "podsumowanie_technologii": {
                    "opis": f"Proficient in {', '.join(extracted_tech[:8])}",
                    "glowne_technologie": extracted_tech[:10],
                    "lata_doswiadczenia": "10+"
                },
                "dopasowanie_do_wymagan": {
                    "mocne_strony": ["Strong technical background", "Extensive experience", "Proven track record"],
                    "poziom_dopasowania": "high",
                    "uzasadnienie": "Candidate meets all key requirements",
                    "rekomendacja": "TAK"
                }
            })
        else:
            analysis.update({
                "basic_data": {
                    "full_name": full_name,
                    "email": email,
                    "phone": phone
                },
                "location_and_availability": {
                    "location": location,
                    "remote_work_preference": "not specified",
                    "availability": "not specified"
                },
                "profile_summary": profile_summary,
                "work_experience": [
                    {
                        "period": job['period'],
                        "company": job['company'],
                        "position": job['position'],
                        "key_achievements": job['description'],
                        "responsibilities": "",
                        "technologies": job.get('technologies', [])
                    }
                    for job in work_experience
                ],
                "education": [
                    {
                        "institution": edu['institution'],
                        "degree": edu['degree'],
                        "field": edu['field'],
                        "period": edu['period']
                    }
                    for edu in education
                ],
                "certifications_and_courses": [],
                "languages": [{"language": "English", "level": "C1"}],
                "skills": {
                    "programming_scripting": categorized_tech.get('programming_scripting', []),
                    "frameworks_libraries": categorized_tech.get('frameworks_libraries', []),
                    "infrastructure_devops": categorized_tech.get('infrastructure_devops', []),
                    "cloud": categorized_tech.get('cloud', []),
                    "databases_messaging": categorized_tech.get('databases_messaging', []),
                    "monitoring": categorized_tech.get('monitoring', []),
                    "other": categorized_tech.get('other', [])
                },
                "tech_stack_summary": {
                    "description": f"Proficient in {', '.join(extracted_tech[:8])}",
                    "primary_technologies": extracted_tech[:10],
                    "years_of_experience": "10+"
                },
                "matching_to_requirements": {
                    "strengths": ["Strong technical background", "Extensive experience", "Proven track record"],
                    "match_level": "high",
                    "justification": "Candidate meets all key requirements",
                    "recommendation": "YES"
                }
            })
        
        print(f"✅ Analysis complete: {len(work_experience)} jobs, {len(education)} education entries")
        return analysis

    
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
        """Apply template filters - IMPROVED"""
        import copy
        filtered = copy.deepcopy(analysis)
        
        if template_type == 'short':
            # Keep only top 3 work experiences
            if 'doswiadczenie_zawodowe' in filtered and len(filtered['doswiadczenie_zawodowe']) > 3:
                filtered['doswiadczenie_zawodowe'] = filtered['doswiadczenie_zawodowe'][:3]
            if 'work_experience' in filtered and len(filtered['work_experience']) > 3:
                filtered['work_experience'] = filtered['work_experience'][:3]
                
            # Keep only 3 certifications
            if 'certyfikaty' in filtered and len(filtered['certyfikaty']) > 3:
                filtered['certyfikaty'] = filtered['certyfikaty'][:3]
                
        elif template_type == 'anonymous':
            # Remove personal data
            if 'podstawowe_dane' in filtered:
                filtered['podstawowe_dane'] = {
                    'imie_nazwisko': 'Kandydat (Anonimowy)',
                    'email': '***@***',
                    'telefon': '***'
                }
            if 'basic_data' in filtered:
                filtered['basic_data'] = {
                    'full_name': 'Candidate (Anonymous)',
                    'email': '***@***',
                    'phone': '***'
                }
                
            # Anonymize company names
            if 'doswiadczenie_zawodowe' in filtered:
                for idx, exp in enumerate(filtered['doswiadczenie_zawodowe']):
                    exp['nazwa_firmy'] = f'Company {idx+1} (Anonymous)'
                    
            # Anonymize universities
            if 'wyksztalcenie' in filtered:
                for idx, edu in enumerate(filtered['wyksztalcenie']):
                    edu['uczelnia'] = f'University {idx+1} (Anonymous)'
                    
        elif template_type == 'extended':
            # Keep everything + add placeholders for interview notes
            pass
        
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
        
    def _extract_technologies_from_cv(self, cv_text):
        """
        STEP 1: Extract ALL technologies from CV text
        This ensures we don't miss anything
        """
        
        prompt = f"""You are a technology extraction specialist.

    CV TEXT:
    {cv_text}

    TASK: Extract EVERY technology, tool, framework, library, methodology mentioned in this CV.

    Look for:
    - Programming languages (Python, Java, Kotlin, C#, etc.)
    - Frameworks (Django, React, Spring, RxJava, Coroutines, etc.)
    - Libraries (Pandas, NumPy, Mockito, JUnit, etc.)
    - Tools (Git, Docker, Jenkins, etc.)
    - Databases (PostgreSQL, MongoDB, Redis, etc.)
    - Cloud (AWS, Azure, GCP, etc.)
    - Mobile (Android, iOS, Jetpack Compose, SwiftUI, etc.)
    - Architecture patterns (MVVM, MVP, MVI, Clean, etc.)
    - DI frameworks (Hilt, Koin, Dagger, etc.)
    - Testing frameworks (Mockito, Espresso, JUnit, etc.)
    - Methodologies (Agile, Scrum, BDD, TDD, etc.)
    - Any other technical terms

    CRITICAL: Extract ONLY what is LITERALLY written in CV. Do not infer or add anything.

    Return ONLY a comma-separated list of technologies, nothing else.

    TECHNOLOGIES:"""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': prompt}],
                options={
                    'temperature': 0.1,
                    'num_predict': 800,
                    'top_p': 0.9
                }
            )
            
            tech_text = response['message']['content'].strip()
            
            # Parse comma-separated list
            tech_list = [t.strip() for t in tech_text.split(',') if t.strip()]
            
            # Clean up
            tech_list = [t for t in tech_list if len(t) > 1 and len(t) < 50]
            
            print(f"🔍 Extracted {len(tech_list)} technologies: {tech_list[:10]}...")
            
            return tech_list
            
        except Exception as e:
            print(f"❌ Technology extraction error: {e}")
            return []


    def _categorize_technologies(self, tech_list):
        """
        STEP 2: Categorize extracted technologies into proper sections
        """
        
        categorized = {
            "programming_scripting": [],
            "frameworks_libraries": [],
            "infrastructure_devops": [],
            "cloud": [],
            "databases_messaging": [],
            "mobile": [],
            "monitoring": [],
            "other": []
        }
        
        # Categorize based on knowledge base
        for tech in tech_list:
            tech_lower = tech.lower()
            placed = False
            
            # Programming
            for known_tech in self.TECH_KNOWLEDGE_BASE.get("programming", []):
                if known_tech.lower() == tech_lower or tech_lower in known_tech.lower():
                    categorized["programming_scripting"].append(tech)
                    placed = True
                    break
            
            if placed:
                continue
                
            # Frameworks
            for known_tech in self.TECH_KNOWLEDGE_BASE.get("frameworks", []):
                if known_tech.lower() == tech_lower or tech_lower in known_tech.lower():
                    categorized["frameworks_libraries"].append(tech)
                    placed = True
                    break
            
            if placed:
                continue
                
            # Mobile
            for known_tech in self.TECH_KNOWLEDGE_BASE.get("mobile", []):
                if known_tech.lower() == tech_lower or tech_lower in known_tech.lower():
                    categorized["mobile"].append(tech)
                    placed = True
                    break
            
            if placed:
                continue
                
            # Infrastructure
            for known_tech in self.TECH_KNOWLEDGE_BASE.get("infrastructure", []):
                if known_tech.lower() == tech_lower or tech_lower in known_tech.lower():
                    categorized["infrastructure_devops"].append(tech)
                    placed = True
                    break
            
            if placed:
                continue
                
            # Cloud
            for known_tech in self.TECH_KNOWLEDGE_BASE.get("cloud", []):
                if known_tech.lower() == tech_lower or tech_lower in known_tech.lower():
                    categorized["cloud"].append(tech)
                    placed = True
                    break
            
            if placed:
                continue
                
            # Databases + Messaging
            for known_tech in (self.TECH_KNOWLEDGE_BASE.get("databases", []) + 
                            self.TECH_KNOWLEDGE_BASE.get("messaging", [])):
                if known_tech.lower() == tech_lower or tech_lower in known_tech.lower():
                    categorized["databases_messaging"].append(tech)
                    placed = True
                    break
            
            if placed:
                continue
                
            # Monitoring
            for known_tech in self.TECH_KNOWLEDGE_BASE.get("monitoring", []):
                if known_tech.lower() == tech_lower or tech_lower in known_tech.lower():
                    categorized["monitoring"].append(tech)
                    placed = True
                    break
            
            if placed:
                continue
                
            # Other
            for known_tech in self.TECH_KNOWLEDGE_BASE.get("other", []):
                if known_tech.lower() == tech_lower or tech_lower in known_tech.lower():
                    categorized["other"].append(tech)
                    placed = True
                    break
            
            # If not categorized, put in frameworks (most common)
            if not placed:
                categorized["frameworks_libraries"].append(tech)
        
        # Merge mobile into frameworks if mobile-specific
        if categorized["mobile"]:
            categorized["frameworks_libraries"].extend(categorized["mobile"])
            categorized["mobile"] = []
        
        print(f"📊 Categorized: programming={len(categorized['programming_scripting'])}, "
            f"frameworks={len(categorized['frameworks_libraries'])}, "
            f"infra={len(categorized['infrastructure_devops'])}, "
            f"db={len(categorized['databases_messaging'])}")
        
        return categorized


    def _extract_work_experience_details(self, cvtext: str) -> list:
        """
        Universal work experience extraction - handles both separate jobs AND project lists.
        """
        import re
        import json

        # 1. Wycięcie sekcji doświadczenia
        patterns = [
            r'(?is)\b(Work History|WORK HISTORY)\b.*?(?=(Education|EDUCATION|Academic Background|Skills|SKILLS|Projects|PROJECTS|Certifications|CERTIFICATIONS|\Z))',
            r'(?is)\b(Work Experience|WORK EXPERIENCE)\b.*?(?=(Education|EDUCATION|Academic Background|Skills|SKILLS|Projects|PROJECTS|Certifications|CERTIFICATIONS|\Z))',
            r'(?is)\b(Professional Experience|PROFESSIONAL EXPERIENCE)\b.*?(?=(Education|EDUCATION|Academic Background|Skills|SKILLS|Projects|PROJECTS|Certifications|CERTIFICATIONS|\Z))',
            r'(?is)\b(Experience|EXPERIENCE)\b.*?(?=(Education|EDUCATION|Academic Background|Skills|SKILLS|Projects|PROJECTS|Certifications|CERTIFICATIONS|\Z))',
            r'(?is)\b(Employment History|EMPLOYMENT HISTORY)\b.*?(?=(Education|EDUCATION|Academic Background|Skills|SKILLS|Projects|PROJECTS|Certifications|CERTIFICATIONS|\Z))',
            r'(?is)\b(Doświadczenie zawodowe|DOŚWIADCZENIE ZAWODOWE)\b.*?(?=(Wykształcenie|WYKSZTAŁCENIE|Edukacja|EDUKACJA|Umiejętności|UMIEJĘTNOŚCI|Projekty|PROJEKTY|\Z))',
            r'(?is)\b(Historia zatrudnienia|HISTORIA ZATRUDNIENIA)\b.*?(?=(Wykształcenie|WYKSZTAŁCENIE|Edukacja|EDUKACJA|Umiejętności|UMIEJĘTNOŚCI|Projekty|PROJEKTY|\Z))',
        ]

        section = None
        for pattern in patterns:
            match = re.search(pattern, cvtext, re.DOTALL | re.IGNORECASE)
            if match and len(match.group(0).strip()) > 400:
                section = match.group(0).strip()
                print(f"💼 Found work section ({len(section)} chars)")
                break

        if not section or len(section) < 400:
            print("⚠️ Work section not found, using full CV for extraction")
            section = cvtext
        else:
            print(f"💼 Work section extracted: {len(section)} chars")

        print("💼 WORK SECTION (last 1000 chars):")
        print(section[-1000:])
        print("=== END WORK SECTION ===")

        # 2. Prompt - obsługa zarówno osobnych firm JAK I project lists
        prompt = f"""Extract ALL WORK EXPERIENCE from this CV. 

    IMPORTANT: Some CVs list ONE position with MULTIPLE PROJECTS/COMPANIES as bullets. Each project/company is a SEPARATE entry.

    Return ONLY a JSON array, no markdown.

    Each entry:
    - "company": company name (or "Project-based" if not specified)
    - "position": job title
    - "period": dates (e.g. "2024-Present", "2016-2020", "From 2016")
    - "description": array of responsibilities/achievements (can be empty)
    - "technologies": array of technologies mentioned (can be empty)

    EXAMPLES FOR PROJECT-BASED EXPERIENCE (like Karol Baran):
    [
    {{"company": "Insurance Company", "position": "Senior Android Developer", "period": "2025-Present", "description": ["Android application in Kotlin/Jetpack Compose for managing insurance"], "technologies": ["Kotlin", "Jetpack Compose"]}},
    {{"company": "International Bank", "position": "Senior Android Developer", "period": "2024-2025", "description": ["Application for leasings, loans, investments"], "technologies": ["Kotlin"]}},
    {{"company": "International Bank", "position": "Senior Android Developer", "period": "2023-2024", "description": ["Jetpack Compose + BDD methodology"], "technologies": ["Kotlin", "Jetpack Compose", "BDD"]}},
    {{"company": "Digital Bank", "position": "Senior Android Developer", "period": "2020-2023", "description": ["USA market, children management"], "technologies": ["Kotlin"]}},
    {{"company": "Navigation", "position": "Android Developer", "period": "2018-2020", "description": ["Maps and navigation, 10M users"], "technologies": ["Java", "Kotlin"]}},
    {{"company": "Fleet management", "position": "Android Developer", "period": "2017-2018", "description": ["Fleet management system"], "technologies": ["Kotlin"]}},
    {{"company": "BLE Connection", "position": "Android Developer", "period": "2016-2017", "description": ["Smart device integration"], "technologies": ["Java", "Kotlin"]}},
    {{"company": "Calendar Reservation", "position": "Android Developer", "period": "2016", "description": ["Booking-like app"], "technologies": ["Java"]}}
    ]

    CRITICAL RULES:
    1. Each bullet/project under ONE position = ONE separate JSON entry
    2. If period is vague (e.g. "2016-Present" for 10 projects), estimate/split periods logically
    3. Extract company names from project descriptions (e.g. "Insurance Company", "Digital Bank")
    4. If no company name, use project name (e.g. "Navigation", "Fleet management")
    5. Keep position consistent across projects (e.g. "Senior Android Developer")
    6. Extract ALL projects - do NOT merge them

    CV TEXT:
    {section[:6000]}
    """

        # 3. LLM call - większy limit dla project lists
        model = getattr(self, "model_name", getattr(self, "modelname", "qwen2.5:14b"))
        try:
            resp = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1, "num_predict": 3500},  # ← 3500 dla 10+ projektów
            )
            responsetext = resp["message"]["content"].strip()
            print(f"📝 RAW WORKEXP LLM ({len(responsetext)} chars):")
            print(responsetext[:800])
        except Exception as e:
            print(f"❌ LLM error: {e}")
            return []

        # 4. Clean JSON
        responsetext = responsetext.replace("``````", "").strip()
        l = responsetext.find("[")
        r = responsetext.rfind("]") + 1

        if l == -1 or r == 0 or r <= l:
            print("❌ No JSON array in response")
            return []

        json_text = responsetext[l:r]
        print(f"🔍 JSON array ({len(json_text)} chars):")
        print(json_text[:600])

        try:
            items = json.loads(json_text)
            if not isinstance(items, list):
                return []
        except Exception as e:
            print(f"❌ JSON parse error: {e}")
            return []

        # 5. Normalizacja
        validjobs = []
        for job in items:
            company = (job.get("company") or job.get("employer") or "").strip()
            position = (job.get("position") or job.get("title") or job.get("role") or "").strip()
            period = (job.get("period") or f"{job.get('start','')}-{job.get('end','')}".strip("- ") or "").strip()
            
            desc = job.get("description", [])
            if isinstance(desc, str):
                desc = [desc] if desc.strip() else []
            elif not isinstance(desc, list):
                desc = []

            tech = job.get("technologies", [])
            if isinstance(tech, str):
                tech = [t.strip() for t in tech.split(",") if t.strip()]
            elif not isinstance(tech, list):
                tech = []

            # Akceptuj jeśli ma position LUB company (minimum)
            if position or company:
                validjobs.append({
                    "company": company,
                    "position": position,
                    "period": period,
                    "description": desc,
                    "technologies": tech,
                })

        print(f"✅ Extracted {len(validjobs)} work experience entries:")
        for i, j in enumerate(validjobs, 1):
            print(f"  {i}. {j['position']} @ {j['company']} ({j['period']}) - {len(j['description'])} bullets")

        return validjobs




    def _extract_education_details(self, cvtext: str) -> list:
        """
        Universal education extraction - handles multi-page sections + internships.
        """
        import re
        import json

        # 1. Wycinanie WSZYSTKICH fragmentów "Edukacja" (także continued)
        header_pattern = r'(?is)\b(Education|Edukacja|Wykształcenie|Studia|Academic|Qualifications)(\s*\(continued\))?\b'
        
        stop_patterns = [
            r'(?is)\b(Skills|Umiejętności|Languages|Języki|Kursy|Szkolenia|Certifications|References|Consent|Nagrody|Publikacje|I hereby)\b',
        ]

        all_matches = []
        for m in re.finditer(header_pattern, cvtext):
            start_pos = m.start()
            remaining = cvtext[start_pos:]
            
            stop_pos = len(remaining)
            for stop_pat in stop_patterns:
                m_stop = re.search(stop_pat, remaining[150:])
                if m_stop:
                    stop_pos = min(stop_pos, 150 + m_stop.start())
                    break
            
            fragment = remaining[:stop_pos].strip()
            if len(fragment) > 100:
                all_matches.append(fragment)
                print(f"🎓 Fragment #{len(all_matches)}: {len(fragment)} chars")

        if all_matches:
            section = "\n\n=== CONTINUED ===\n\n".join(all_matches)
            print(f"🎓 Total education: {len(section)} chars from {len(all_matches)} sections")
        else:
            print("⚠️ No education, using full CV")
            section = cvtext

        print("🎓 LAST 1200 CHARS OF SECTION:")
        print(section[-1200:])
        print("=== END ===")

        # 2. Prompt - WYMUSZENIE osobnych wpisów
        prompt = f"""Extract ALL education entries from this CV. Each degree, internship, or academic stay is a SEPARATE entry.

    Return ONLY a JSON array, no markdown.

    Each entry:
    - "institution": university name
    - "degree": Doktorat/PhD/Master/Bachelor/Staż doktorancki/Inżynier/Magister Inżynier
    - "field": field of study (can be empty for internships)
    - "period": dates (e.g. "2018-2022", "2022", "2017-2018")

    CRITICAL RULES:
    1. "Staż doktorancki" (doctoral internship) is a SEPARATE entry - do NOT merge with PhD
    2. "Magister Inżynier" and "Inżynier" at the SAME university are TWO entries (even if same dates)
    3. Each line starting with a degree title or institution is a NEW entry
    4. Do NOT merge entries with same university or dates

    EXAMPLES (from this CV):
    [
    {{"institution": "Politechnika Śląska", "degree": "Doktorat", "field": "Mechanika Obliczeniowa", "period": "2018-2022"}},
    {{"institution": "Montanuniversität Leoben", "degree": "Staż doktorancki", "field": "energia odnawialna", "period": "2022"}},
    {{"institution": "Cranfield University", "degree": "Staż doktorancki", "field": "przepływy supersoniczne", "period": "2022"}},
    {{"institution": "Cranfield University", "degree": "Master of Science", "field": "Computational Fluid Dynamics", "period": "2017-2018"}},
    {{"institution": "Politechnika Śląska", "degree": "Magister Inżynier", "field": "Mechanika i Budowa Maszyn", "period": "2013-2017"}},
    {{"institution": "Politechnika Śląska", "degree": "Inżynier", "field": "Mechanika i Budowa Maszyn", "period": "2013-2017"}}
    ]

    CV TEXT:
    {section[:5500]}
    """

        # 3. LLM - większy limit dla 6 wpisów
        model = getattr(self, "model_name", getattr(self, "modelname", "qwen2.5:14b"))
        try:
            resp = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.0, "num_predict": 2000},  # ← 2000 dla 6 wpisów
            )
            raw = resp["message"]["content"].strip()
            print(f"📝 RAW LLM ({len(raw)} chars):")
            print(raw[:600])
        except Exception as e:
            print(f"❌ LLM error: {e}")
            return []

        # 4. Clean JSON
        raw = raw.replace("``````", "").strip()
        l = raw.find("[")
        r = raw.rfind("]") + 1
        
        if l == -1 or r == 0 or r <= l:
            print("❌ No JSON array")
            return []

        json_text = raw[l:r]
        print(f"🔍 JSON array ({len(json_text)} chars):")
        print(json_text[:500])

        try:
            data = json.loads(json_text)
            if not isinstance(data, list):
                return []
        except Exception as e:
            print(f"❌ JSON parse error: {e}")
            print(f"Failed JSON: {json_text[:400]}")
            return []

        # 5. Normalizacja
        normalized = []
        for e in data:
            period = (
                e.get("period")
                or f"{e.get('start','')}-{e.get('end','')}".strip("- ")
                or e.get("dates", "")
            )

            institution = (e.get("institution") or e.get("university") or e.get("school") or "").strip()
            degree = (e.get("degree") or e.get("title") or e.get("level") or "").strip()
            field = (e.get("field") or e.get("major") or e.get("specialization") or "").strip()
            period = " ".join(period.split())

            if degree or institution:
                normalized.append({
                    "institution": institution,
                    "degree": degree,
                    "field": field,
                    "period": period,
                })

        print(f"✅ Extracted {len(normalized)} education entries:")
        for i, e in enumerate(normalized, 1):
            print(f"  {i}. {e['degree']} {e['field']} @ {e['institution']} ({e['period']})")

        return normalized




    def _create_polish_prompt(self, cv_text, client_requirements, needs_translation=False, source_lang='polish'):
        """
        IMPROVED: Uses extracted work experience and education directly
        """
        
        # Pre-extract all work experience and education
        extracted_work_exp = self._extract_work_experience_details(cv_text)
        extracted_education = self._extract_education_details(cv_text)
        extracted_tech = self._extract_technologies_from_cv(cv_text)
        categorized_tech = self._categorize_technologies(extracted_tech)
        
        prompt = "Jesteś ekspertem HR specjalizującym się w analizie CV.\n\n"
        
        if needs_translation:
            prompt += f"WAŻNE: CV jest napisane po {self._get_language_name(source_lang, 'pl')}. "
            prompt += "Przeanalizuj je i wygeneruj raport PO POLSKU.\n\n"
        
        prompt += "TREŚĆ CV KANDYDATA:\n" + cv_text + "\n\n"
        prompt += "WYMAGANIA KLIENTA:\n" + client_requirements + "\n\n"
        
        # Extracted technologies
        prompt += "=" * 80 + "\n"
        prompt += "TECHNOLOGIE Z CV (UŻYJ WSZYSTKICH):\n"
        prompt += "=" * 80 + "\n\n"
        
        for category, techs in categorized_tech.items():
            if techs:
                prompt += f"{category}: {', '.join(techs)}\n"
        
        prompt += "\n" + "=" * 80 + "\n"
        
        # Extracted work experience
        prompt += "DOŚWIADCZENIE ZAWODOWE (UŻYJ WSZYSTKICH WPISÓW):\n"
        prompt += "=" * 80 + "\n\n"
        
        for idx, exp in enumerate(extracted_work_exp, 1):
            prompt += f"{idx}. {exp['period']} | {exp['company']} | {exp['position']}\n"
            if exp['description']:
                prompt += f"   Opis: {exp['description']}\n"
            if exp['technologies']:
                prompt += f"   Tech: {', '.join(exp['technologies'])}\n"
        
        prompt += "\n" + "=" * 80 + "\n"
        
        # Extracted education
        prompt += "EDUKACJA (UŻYJ WSZYSTKICH WPISÓW I DOKŁADNIE TEŻ DATY):\n"
        prompt += "=" * 80 + "\n\n"
        
        for idx, edu in enumerate(extracted_education):
            prompt += f""" {{
        "uczelnia": "{edu['institution']}",
        "stopien": "{edu['degree']}",
        "kierunek": "{edu['field']}",
        "okres": "{edu['period']}"
        }}{'' if idx == len(extracted_education) - 1 else ','}
        """
        
        prompt += "\n" + "=" * 80 + "\n\n"
        
        prompt += """Wygeneruj szczegółowy raport w formacie JSON PO POLSKU:

    🚨 KRYTYCZNE - OBOWIĄZKOWE:
    1. Liczba wpisów w "doswiadczenie_zawodowe" = liczba wpisów z powyższej listy
    2. Liczba wpisów w "wyksztalcenie" = liczba wpisów z powyższej listy
    3. KAŻDY wpis z listy MUSI być w JSON, NIE pomijaj ani nie łącz!
    4. Daty w edukacji - przepisz DOKŁADNIE jak w liście, bez zmian
    5. Technologie z każdego wpisu doświadczenia - WSZYSTKIE w "technologie"

    {
    "podstawowe_dane": {
        "imie_nazwisko": "Wyciągnij z CV",
        "email": "Email lub: nie podano",
        "telefon": "Telefon lub: nie podano"
    },
    "lokalizacja_i_dostepnosc": {
        "lokalizacja": "Dokładna lokalizacja TYLKO jeśli jasno podana, inaczej: nie podano",
        "preferencja_pracy_zdalnej": "Zdalna/Hybrydowa/Stacjonarna/nieokreślona",
        "dostepnosc": "Okres wypowiedzenia lub: nieokreślona"
    },
    "podsumowanie_profilu": "Krótka analiza 3-5 zdań kandydata",
    "doswiadczenie_zawodowe": ["""
        
        # Add each work experience entry
        for idx, exp in enumerate(extracted_work_exp):
            prompt += f"""    {{
        "okres": "{exp['period']}",
        "firma": "{exp['company']}",
        "stanowisko": "{exp['position']}",
        "kluczowe_osiagniecia": {json.dumps([exp['description']] if exp['description'] else [], ensure_ascii=False)},
        "obowiazki": [],
        "technologie": {json.dumps(exp['technologies'], ensure_ascii=False)}
        }}{'' if idx == len(extracted_work_exp) - 1 else ','}
    """
        
        prompt += """  ],
    "wyksztalcenie": ["""
        
        # Add each education entry
        for idx, edu in enumerate(extracted_education):
            prompt += f"""    {{
        "uczelnia": "{edu['uczelnia']}",
        "stopien": "{edu['stopien']}",
        "kierunek": "{edu['kierunek']}",
        "okres": "{edu['okres']}"
        }}{'' if idx == len(extracted_education) - 1 else ','}
    """
        
        prompt += """  ],
    "certyfikaty_i_kursy": [
        {
        "nazwa": "Nazwa certyfikatu",
        "typ": "certyfikat",
        "wystawca": "Organizacja",
        "data": "Rok"
        }
    ],
    "jezyki_obce": [
        {"jezyk": "Język ojczysty", "poziom": "Ojczysty"}
    ],
    "umiejetnosci": {
        "programowanie_skrypty": """ + json.dumps(categorized_tech.get('programming_scripting', []), ensure_ascii=False) + """,
        "frameworki_biblioteki": """ + json.dumps(categorized_tech.get('frameworks_libraries', []), ensure_ascii=False) + """,
        "infrastruktura_devops": """ + json.dumps(categorized_tech.get('infrastructure_devops', []), ensure_ascii=False) + """,
        "chmura": """ + json.dumps(categorized_tech.get('cloud', []), ensure_ascii=False) + """,
        "bazy_kolejki": """ + json.dumps(categorized_tech.get('databases_messaging', []), ensure_ascii=False) + """,
        "monitoring": """ + json.dumps(categorized_tech.get('monitoring', []), ensure_ascii=False) + """,
        "inne": """ + json.dumps(categorized_tech.get('other', []), ensure_ascii=False) + """
    },
    "podsumowanie_technologii": {
        "opis": "Podsumowanie głównych technologii",
        "glowne_technologie": """ + json.dumps(extracted_tech[:10], ensure_ascii=False) + """,
        "lata_doswiadczenia": "X lat"
    },
    "dopasowanie_do_wymagan": {
        "mocne_strony": ["Mocna strona 1", "Mocna strona 2"],
        "poziom_dopasowania": "wysoki/sredni/niski",
        "uzasadnienie": "Szczegółowe uzasadnienie",
        "rekomendacja": "TAK/NIE"
    }
    }
    """
        
        return prompt


    
    def _create_english_prompt(self, cv_text, client_requirements, needs_translation=False, source_lang='english'):
        """ENHANCED English prompt with pre-extracted technologies"""
        
        # STEP 1: Extract technologies first
        extracted_tech = self._extract_technologies_from_cv(cv_text)
        categorized_tech = self._categorize_technologies(extracted_tech)
        
        prompt = "You are an expert HR professional specializing in CV analysis.\n\n"
        
        if needs_translation:
            prompt += f"IMPORTANT: CV is written in {self._get_language_name(source_lang, 'en')}. "
            prompt += "Analyze it and generate a comprehensive report IN ENGLISH, translating all information.\n\n"
        
        prompt += "CV TEXT:\n" + cv_text + "\n\n"
        prompt += "CLIENT REQUIREMENTS:\n" + client_requirements + "\n\n"
        
        # CRITICAL: Provide extracted technologies
        prompt += "=" * 80 + "\n"
        prompt += "TECHNOLOGIES EXTRACTED FROM CV (USE ALL OF THEM!):\n"
        prompt += "=" * 80 + "\n\n"
        
        for category, techs in categorized_tech.items():
            if techs:
                prompt += f"{category}: {', '.join(techs)}\n"
        
        prompt += "\n" + "=" * 80 + "\n\n"
        
        prompt += "Generate a comprehensive report in JSON format IN ENGLISH:\n"
        prompt += '{\n'
        
        # Basic data
        prompt += ' "basic_data": {\n'
        prompt += ' "full_name": "Extract name and surname from CV",\n'
        prompt += ' "email": "Email or: not provided",\n'
        prompt += ' "phone": "Phone or: not provided"\n'
        prompt += ' },\n'
        
        # Location
        prompt += '"location_and_availability": {\n'
        prompt += '"location": "Exact location (city and country) ONLY if it is clearly stated in the CV. \n'
        prompt += 'If there are only generic hints (e.g. Poland, Remote, EU), set: unclear / not provided.",\n'
        prompt += '"remote_work_preference": "Remote / Hybrid / On-site or: not specified",\n'
        prompt += '"availability": "Notice period or: not specified"\n'
        prompt += '},\n'
        
        # Profile summary
        prompt += ' "profile_summary": "IMPORTANT: Write YOUR OWN analysis (3-5 sentences). Include: experience, competencies, match to requirements, recommendation.",\n'
        
        # Work experience
        prompt += ' "work_experience": [\n'
        prompt += ' {\n'
        prompt += ' "period": "YYYY - YYYY or YYYY - Present",\n'
        prompt += ' "company": "Company name",\n'
        prompt += ' "position": "Position title",\n'
        prompt += ' "key_achievements": ["List of achievements with specific numbers/results"],\n'
        prompt += ' "responsibilities": ["Optional - detailed responsibilities"],\n'
        prompt += ' "technologies": ["Technologies used in this period"]\n'
        prompt += ' }\n'
        prompt += ' ],\n'
        
        # Education
        prompt += ' "education": [\n'
        prompt += ' {\n'
        prompt += ' "institution": "University name",\n'
        prompt += ' "degree": "Bachelor/Master/PhD",\n'
        prompt += ' "field": "Field of study",\n'
        prompt += ' "period": "YYYY - YYYY"\n'
        prompt += ' }\n'
        prompt += ' ],\n'
        
        # Certifications
        prompt += ' "certifications_and_courses": [\n'
        prompt += ' {\n'
        prompt += ' "name": "Certification or course name",\n'
        prompt += ' "type": "certification or course",\n'
        prompt += ' "issuer": "Organization/Platform",\n'
        prompt += ' "date": "Year"\n'
        prompt += ' }\n'
        prompt += ' ],\n'
        
        # Languages
        prompt += ' "languages": [\n'
        prompt += ' {"language": "Language name", "level": "A1/A2/B1/B2/C1/C2/Native"}\n'
        prompt += ' ],\n'
        
        # Skills - USE EXTRACTED TECHNOLOGIES
        prompt += ' "skills": {\n'
        prompt += f' "programming_scripting": {json.dumps(categorized_tech["programming_scripting"])},\n'
        prompt += f' "frameworks_libraries": {json.dumps(categorized_tech["frameworks_libraries"])},\n'
        prompt += f' "infrastructure_devops": {json.dumps(categorized_tech["infrastructure_devops"])},\n'
        prompt += f' "cloud": {json.dumps(categorized_tech["cloud"])},\n'
        prompt += f' "databases_messaging": {json.dumps(categorized_tech["databases_messaging"])},\n'
        prompt += f' "monitoring": {json.dumps(categorized_tech["monitoring"])},\n'
        prompt += f' "other": {json.dumps(categorized_tech["other"])}\n'
        prompt += ' },\n'
        
        # Tech stack summary
        prompt += ' "tech_stack_summary": {\n'
        prompt += ' "description": "Brief summary of candidate main technologies",\n'
        prompt += ' "primary_technologies": ["Top 8-10 most important technologies from above list"],\n'
        prompt += ' "years_of_experience": "X years of IT experience"\n'
        prompt += ' },\n'
        
        # Matching
        prompt += ' "matching_to_requirements": {\n'
        prompt += ' "strengths": ["At least 3 strengths related to requirements"],\n'
        prompt += ' "match_level": "high/medium/low",\n'
        prompt += ' "justification": "Detailed justification with specific examples",\n'
        prompt += ' "recommendation": "YES - recommend for further process / NO - does not meet requirements"\n'
        prompt += ' }\n'
        prompt += '}\n\n'
        
        prompt += "CRITICAL INSTRUCTIONS:\n"
        prompt += "1. USE ALL technologies from the list above in the 'skills' section\n"
        prompt += "2. Extract ALL work experience information\n"
        prompt += "3. DO NOT ADD technologies that are not in the CV\n"
        prompt += "4. RETURN valid JSON with ALL fields filled\n\n"
        
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
        import re  # Dodaj na początku funkcji
        
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
    


    def _extract_keywords_from_requirements(self, client_requirements):
        """Extract ONLY key technologies and experience years from client requirements"""
        if not client_requirements or len(client_requirements) < 5:
            return []
        
        keywords = []
        requirements_lower = client_requirements.lower()
        
        # 1. Extract ONLY technologies from knowledge base (no common words)
        for category, tech_list in self.TECH_KNOWLEDGE_BASE.items():
            for tech in tech_list:
                tech_lower = tech.lower()
                # Only add if it's a real technology (not common words)
                if tech_lower in requirements_lower and len(tech) > 2:
                    keywords.append(tech_lower)
        
        # 2. Extract experience years (numbers followed by 'years', 'lat', 'rok')
        import re
        # Match patterns like "5 lat", "3 years", "5+ lat"
        year_patterns = re.findall(r'(\d+)\+?\s*(?:lat|lata|year|years|rok|lata)', requirements_lower)
        keywords.extend(year_patterns)
        
        # 3. Extract seniority levels (ONLY if explicitly mentioned)
        seniority = ['senior', 'junior', 'mid-level', 'lead', 'principal', 'architect']
        for level in seniority:
            if level in requirements_lower:
                keywords.append(level)
        
        # Remove duplicates and filter out common words
        keywords = list(set(keywords))
        
        # FILTER OUT common words that shouldn't be highlighted
        excluded_words = [
            'experience', 'doświadczenie', 'znajomość', 'knowledge', 
            'umiejętność', 'praca', 'work', 'projekt', 'project',
            'aplikacja', 'application', 'system', 'develop', 'rozwój',
            'z', 'w', 'na', 'do', 'i', 'or', 'and', 'the', 'a', 'an'
        ]
        keywords = [kw for kw in keywords if kw not in excluded_words and len(kw) > 2]
        
        print(f"🎯 Filtered keywords (technologies + years): {keywords}")
        return keywords



    def _text_contains_keyword(self, text, keywords):
        """Check if text contains any of the keywords"""
        if not keywords or not text:
            return False
        
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)


    def _write_text_with_underline(self, pdf, text, x, y, width, font_name, font_size, keywords, line_height=5, bold=False):
        """
        Write multi-line text with underlined keywords
        Returns final Y position
        """
        if not text or text in ["NA", "Nie podano w CV", "not provided"]:
            return y
        
        if not keywords:
            # No keywords - regular text
            pdf.set_xy(x, y)
            pdf.set_font(font_name, 'B' if bold else '', 9)
            pdf.multi_cell(width, line_height, text, align='L')
            return pdf.get_y()
        
        # Split into words
        words = str(text).split()
        current_line = []
        current_y = y
        
        pdf.set_font(font_name, 'B' if bold else '', 9)
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            
            # Check if line would be too wide
            if pdf.get_string_width(test_line) > width and current_line:
                # Write current line
                pdf.set_xy(x, current_y)
                self._write_line_with_keywords(pdf, ' '.join(current_line), font_name, font_size, keywords, bold)
                current_y += line_height
                current_line = [word]
            else:
                current_line.append(word)
        
        # Write remaining words
        if current_line:
            pdf.set_xy(x, current_y)
            self._write_line_with_keywords(pdf, ' '.join(current_line), font_name, font_size, keywords, bold)
            current_y += line_height
        
        return current_y


    def _write_line_with_keywords(self, pdf, line, font_name, font_size, keywords, bold=False):
        """Write a single line with BOLD keywords (instead of underline)"""
        words = line.split()
        
        for i, word in enumerate(words):
            # Check if word contains keyword
            word_lower = word.lower().strip('.,;:!?()"\'')
            has_keyword = any(
                                kw.lower() == word_lower or kw.lower() in word_lower 
                                for kw in keywords
                            ) if keywords else False
            
            # Set style - BOLD for keywords
            if has_keyword:
                style = 'B'  # Bold for matching keywords
            elif bold:
                style = 'B'  # Bold if requested
            else:
                style = ''   # Normal text
            
            pdf.set_font(font_name, style, 9)
            pdf.write(font_size * 0.7, word + (' ' if i < len(words)-1 else ''))


    def extract_raw_experience_block(self, cv_text):
        # Look for the "Doświadczenie zawodowe" (case-insensitive)
        import re
        start = re.search(r"doświadczenie zawodowe", cv_text, re.IGNORECASE)
        if not start:
            return ""
        start_idx = start.start()
        # Search for the next main header (e.g. "Wykształcenie", "Umiejętności", etc.)
        end = re.search(r"\n[A-ZĄĆĘŁŃÓŚŹŻ ]{5,}\n", cv_text[start_idx:], re.IGNORECASE)
        if end:
            end_idx = start_idx + end.start()
            return cv_text[start_idx:end_idx].strip()
        else:
            return cv_text[start_idx:].strip()
      
    def generate_pdf_output(self, analysis, template_type='full', language=None, client_requirements=''):
        """Generate PDF with FPDF2 - Arsenal font - 2 pages layout"""
        
        filtered_analysis = self.apply_template_filters(analysis, template_type)
        if language is None:
            language = filtered_analysis.get('output_language', 'en')
        # Font paths
        arsenal_regular = r'C:\Users\Kamil Czyżewski\OneDrive - Integral Solutions sp. z o.o\Pulpit\Projects\HR_CV_Analyzer\arsenal\Arsenal-Regular.ttf'#
        arsenal_bold = r'C:\Users\Kamil Czyżewski\OneDrive - Integral Solutions sp. z o.o\Pulpit\Projects\HR_CV_Analyzer\arsenal\Arsenal-Bold.ttf'#"/app/arsenal/Arsenal-Bold.ttf"
        keywords = self._extract_keywords_from_requirements(client_requirements)
        print(f"🔍 Extracted {len(keywords)} keywords for highlighting: {keywords[:10]}")
        print(f"📝 Client requirements: {client_requirements[:100]}...")

        # ✅ POPRAWNE:
        def safe_text(text, default='N/A'):
            if text is None or text == '':
                return default
            return str(text)

        
        def get_section_name(en_name):
            """Polish translation"""
            output_lang = filtered_analysis.get('output_language', 'english')
            
            translations = {
                'K E Y  H I G H L I G H T S':'P O D S U M O W A N I E  P R O F I L U',
                'E D U C A T I O N': 'W Y K S Z T A Ł C E N I E',
                'L A N G U A G E S': 'J Ę Z Y K I',
                'C E R T I F I C A T I O N S': 'C E R T Y F I K A T Y',
                'P R O F I L E  S U M M A R Y': 'R E K O M E N D A C J A',
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
            pdf.set_font('Arsenal', '', 10)
        except Exception as e:
            print(f"Font error: {e}")
            # Fallback to built-in Helvetica font (always available in FPDF2)
            pdf.set_font('Helvetica', '', 10)
        
        # Set margins
        pdf.set_margins(left=12.7, top=0, right=12.7)
        
        # ===== PAGE 1: HEADER + PROFILE SUMMARY (BULLET POINTS ONLY) =====
        
        # Blue header
        pdf.set_fill_color(50, 130, 180)
        pdf.rect(0, 0, 210, 40, 'F')
        
        # Logo
        logo_path = r'C:\Users\Kamil Czyżewski\OneDrive - Integral Solutions sp. z o.o\Pulpit\Projects\HR_CV_Analyzer\IS_New.png'#"/app/IS_New.png"
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
        # Najpierw spróbuj dzielić po bulletach
            highlights = [h.strip() for h in profile_summary.split('•') if h.strip()]
            
            if not highlights:

                sentences = re.split(r'\.\s+(?=[A-Z])', profile_summary)
                highlights = []
                for s in sentences:
                    s = s.strip()
                    if len(s) > 10:  # Minimum 10 znaków
                        # Dodaj kropkę jeśli brak
                        if not s.endswith('.'):
                            s = s + '.'
                        highlights.append(s)
                    if len(highlights) >= 6:
                        break
            
            filtered_analysis['mocne_strony'] = highlights[:6]
        
        # ===== DISPLAY KEY HIGHLIGHTS ON PAGE 1 =====
        highlights = filtered_analysis.get("key_highlights", [])

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
                    sentences = re.split(r'\.\s+(?=[A-Z])', profile_text)
                    highlights = []
                    for s in sentences:
                        s = s.strip()
                        if len(s) > 10:
                            if not s.endswith('.'):
                                s = s + '.'
                            highlights.append(s)
                        if len(highlights) >= 6:
                            break

        # Teraz zawsze wyświetl
        if highlights:
            pdf.set_font('Arsenal', 'B', 13)
            # Domyślnie 'en' jeśli brak parametru
            pdf_language = language if language else 'en'
            pdf.cell(0, 5, get_section_name('K E Y  H I G H L I G H T S'), ln=True)
            
            # Underline
            pdf.set_draw_color(76, 76, 76)
            pdf.set_line_width(0.3)
            y_before = pdf.get_y()
            pdf.line(12.7, y_before, 197.3, y_before)
            pdf.set_draw_color(0, 0, 0)
            
            pdf.set_y(y_before + 3)
            pdf.set_x(12.7)
            
            pdf.set_font('Arsenal', '', 11)
            
            for highlight in highlights:
                highlight_text = safe_text(highlight).strip()
                if highlight_text:
                    pdf.set_x(12.7)
                    current_y = self._write_text_with_underline(
                                pdf, f"• {highlight_text}", 12.7, pdf.get_y(),
                                185, 'Arsenal', 10, keywords, line_height=5
                            )
                    pdf.set_y(current_y)
                    
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
        
        def add_text_column(x, text, font_size=9, max_width=45):
            """Add wrapped text to column"""
            pdf.set_font('Arsenal', '', font_size)
            pdf.set_xy(x, pdf.get_y())
            pdf.multi_cell(max_width, 4, text, align='L')
        
        def add_bold_text_column(x, text, font_size=9, max_width=45):
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
                ('mobile', 'mobile', 'Mobile'),
                ('infrastruktura_devops', 'infrastructure_devops', 'Infrastructure'),
                ('chmura', 'cloud', 'Cloud'),
                ('bazy_kolejki', 'databases_messaging', 'Data'),
                ('monitoring', 'monitoring', 'Monitoring'),
                ('inne', 'other', 'Other'),
            ]

            for pl_key, en_key, label in skill_cats:
                skills_list = skills_data.get(pl_key) or skills_data.get(en_key)
                if not skills_list:
                    continue

                skills_str = ", ".join(safe_text(s) for s in skills_list)

                # Label - bold (na osobnej linii, mały odstęp przed)
                pdf.set_xy(col_left_x + 2, pdf.get_y() + 1)
                add_bold_text_column(col_left_x + 2, f"{label}:", 8, col_left_width - 4)

                # Technologies - normal, mały font, niższa linia
                pdf.set_xy(col_left_x + 2, pdf.get_y())
                current_y = self._write_text_with_underline(
                    pdf,
                    skills_str,
                    col_left_x + 2,
                    pdf.get_y(),
                    col_left_width - 4,
                    'Arsenal',
                    7,
                    keywords,
                    line_height=3.8
                )
                pdf.set_y(current_y + 1)
        
        # TECH STACK
        tech_summary = filtered_analysis.get("podsumowanie_technologii") or filtered_analysis.get("tech_stack_summary")
        if tech_summary:
            pdf.set_xy(col_left_x, pdf.get_y())
            y_left = add_section_header(col_left_x, get_section_name('T E C H  S T A C K'), col_left_width)
            pdf.set_y(y_left)
            description = tech_summary.get('opis') or tech_summary.get('description')
            if description:
                pdf.set_xy(col_left_x + 2, pdf.get_y())
                add_text_column(col_left_x + 2, safe_text(description), 9, col_left_width - 4)
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
                add_text_column(col_left_x + 2, f"{language}: {level}", 9, col_left_width - 4)
            
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
                add_bold_text_column(col_left_x + 2, item_name, 9, col_left_width - 4)
                pdf.set_xy(col_left_x + 2, pdf.get_y())
                add_text_column(col_left_x + 2, issuer, 9, col_left_width - 4)
            
            pdf.set_y(pdf.get_y() + 2)
        
        # ===== RIGHT COLUMN: PROFILE SUMMARY (FULL TEXT), WORK EXPERIENCE, EDUCATION =====
        
        # PROFILE SUMMARY - FULL TEXT (na drugiej stronie)
        right_start_y = 50
        pdf.set_y(right_start_y)

        # PROFILE SUMMARY - FULL TEXT
        profile_summary = filtered_analysis.get('podsumowanie_profilu') or filtered_analysis.get('profile_summary')

        if profile_summary and profile_summary not in ["NA", "Nie podano w CV", "not provided", ""]:
            pdf.set_xy(col_right_x, right_start_y)
            y_right = add_section_header(
                col_right_x,
                get_section_name('P R O F I L E  S U M M A R Y'),
                col_right_width
            )
            pdf.set_y(y_right)

            profile_text = safe_text(profile_summary).replace('•', '').strip()

            current_y = self._write_text_with_underline(
                pdf,
                profile_text,
                col_right_x + 2,
                pdf.get_y(),
                col_right_width - 4,
                'Arsenal',
                8,          # mniejszy font
                keywords,
                line_height=4
            )
            pdf.set_y(current_y + 3)
        else:
            pdf.set_y(right_start_y)

        # ===== WORK EXPERIENCE =====
        work_exp_data = filtered_analysis.get("doswiadczenie_zawodowe") or filtered_analysis.get("work_experience", [])

        if work_exp_data:
            pdf.set_xy(col_right_x, pdf.get_y())
            y_right = add_section_header(col_right_x, get_section_name("WORK EXPERIENCE"), col_right_width)
            pdf.set_y(y_right)
            
            for idx, exp in enumerate(work_exp_data):
                if idx > 0:
                    pdf.ln(4)
                
                period = safe_text(exp.get("okres") or exp.get("period"), "")
                company = safe_text(exp.get("firma") or exp.get("company"), "")
                position = safe_text(exp.get("stanowisko") or exp.get("position"), "")
                achievements = exp.get("kluczowe_osiagniecia") or exp.get("key_achievements") or []
                technologies = exp.get("technologie") or exp.get("technologies") or []
                
                # PERIOD
                if period not in ("", "YYYY - YYYY", "Not specified", "NA"):
                    pdf.set_xy(col_right_x + 2, pdf.get_y())
                    pdf.set_font("Arsenal", "B", 8)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(0, 4, period, ln=True)
                    pdf.set_text_color(0, 0, 0)
                
                # POSITION
                if position not in ("", "NA", "Not specified"):
                    pdf.set_xy(col_right_x + 2, pdf.get_y())
                    pdf.set_font("Arsenal", "B", 9)
                    pdf.multi_cell(col_right_width - 4, 4, position, align="L")
                
                # COMPANY
                if company not in ("", "NA", "Not specified"):
                    pdf.set_xy(col_right_x + 2, pdf.get_y())
                    pdf.set_font("Arsenal", "B", 8)
                    pdf.multi_cell(col_right_width - 4, 4, company, align="L")
                
                # ACHIEVEMENTS
                if achievements and isinstance(achievements, list):
                    pdf.set_font("Arsenal", "", 8)
                    for ach in achievements:
                        bullet_text = safe_text(ach, "").strip()
                        if bullet_text and len(bullet_text) > 3:
                            pdf.set_x(col_right_x + 4)
                            pdf.multi_cell(col_right_width - 6, 4, f"• {bullet_text}", align="L")
                            pdf.ln(0.5)
                
                # TECH
                if technologies:
                    tech_list = technologies if isinstance(technologies, list) else [technologies]
                    tech_str = ", ".join([safe_text(t, "") for t in tech_list if safe_text(t, "")])
                    if tech_str:
                        pdf.set_x(col_right_x + 4)
                        pdf.set_font("Arsenal", "", 7)
                        pdf.set_text_color(80, 80, 80)
                        pdf.multi_cell(col_right_width - 6, 3.5, f"Tech: {tech_str}", align="L")
                        pdf.set_text_color(0, 0, 0)

                pdf.ln(3)

                # Spacing between jobs
                pdf.set_y(pdf.get_y() + 3)

        # ===== EDUCATION =====
        education_data = filtered_analysis.get('wyksztalcenie') or filtered_analysis.get('education', [])
        print(f"\n🎓 DEBUG generate_pdf_output educationdata: {len(education_data)} items")
        for i, edu in enumerate(education_data[:5]):
            print(f"  {i+1}. uczelnia={edu.get('uczelnia') or edu.get('school')}, "
                f"kierunek={edu.get('kierunek') or edu.get('degree')}, "
                f"okres={edu.get('okres') or edu.get('period')}")
            
        if education_data:
            pdf.set_xy(col_right_x, pdf.get_y() + 3)
            y_right = add_section_header(
                col_right_x,
                get_section_name('E D U C A T I O N'),
                col_right_width
            )
            pdf.set_y(y_right + 1)

            for edu in education_data:
                institution = safe_text(edu.get('uczelnia') or edu.get('institution', ''))
                degree = safe_text(edu.get('stopien') or edu.get('degree', ''))
                field = safe_text(edu.get('kierunek') or edu.get('field_of_study') or edu.get('field', ''))
                period = safe_text(edu.get('okres') or edu.get('period', ''))

                # Period – bold, 8 (szary)
                if period and period not in ['YYYY - YYYY', 'Not specified', '', 'N/A']:
                    pdf.set_xy(col_right_x + 2, pdf.get_y())
                    pdf.set_font('Arsenal', 'B', 8)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(0, 4, period, ln=True)
                    pdf.set_text_color(0, 0, 0)

                # Field + Degree – bold, 8
                if field or degree:
                    text_fd = f"{field}, {degree}" if field and degree else (field or degree)
                    pdf.set_xy(col_right_x + 2, pdf.get_y())
                    pdf.set_font('Arsenal', 'B', 8)
                    pdf.multi_cell(col_right_width - 4, 4, text_fd, align='L')

                # Institution – normal, 8
                if institution and institution not in ['Nazwa uczelni', 'Not specified', '', 'N/A']:
                    if institution and institution not in ["Nazwa uczelni", "Not specified", "", "NA"]:
                        pdf.set_xy(col_right_x + 2, pdf.get_y())
                        pdf.set_font('Arsenal', '', 8)
                        pdf.multi_cell(col_right_width - 4, 4, institution, align='L')

                # mały odstęp, nie +5
                pdf.set_y(pdf.get_y() + 2)

        # ===== GENERATE KEY HIGHLIGHTS FROM PROFILE SUMMARY =====
        profile_text = filtered_analysis.get("podsumowanie_profilu") or filtered_analysis.get("profile_summary") or ""
        
        # Generate highlights if they don't exist yet
        if profile_text and not filtered_analysis.get("mocne_strony"):
            # Try splitting by bullets first
            highlights = [h.strip() for h in profile_text.split('•') if h.strip()]
            
            # If no bullets, split by sentences
            if not highlights or len(highlights) < 2:
                sentences = re.split(r'\.\s+(?=[A-Z])', profile_text)
                highlights = []
                for s in sentences:
                    s = s.strip()
                    if len(s) > 10:
                        if not s.endswith('.'):
                            s = s + '.'
                        highlights.append(s)
                    if len(highlights) >= 6:
                        break
            
            filtered_analysis['mocne_strony'] = highlights[:6] if highlights else []
        # Save to buffer
        buffer = BytesIO()
        pdf.output(buffer)
        buffer.seek(0)
        return buffer
    
    def generate_docx_output(self, analysis, template_type='full', language=None, client_requirements=''):
        """Generate DOCX with Arsenal font - all headers with underlines"""

        keywords = self._extract_keywords_from_requirements(client_requirements)

        filtered_analysis = self.apply_template_filters(analysis, template_type)
        if language is None:
            language = filtered_analysis.get('output_language', 'en')
        
        # Arsenal font path
        arsenal_regular = r'C:\Users\Kamil Czyżewski\OneDrive - Integral Solutions sp. z o.o\Pulpit\Projects\HR_CV_Analyzer\arsenal\Arsenal-Regular.ttf'#"/app/arsenal/Arsenal-Regular.ttf"
        
        def safe_text(value, default=''):
            return str(value).strip() if value and str(value).strip() not in ['None', 'null', 'N/A'] else default
        
        def get_section_name(en_name):
            output_lang = filtered_analysis.get('output_language', 'english')
            translations = {
                'K E Y  H I G H L I G H T S': 'P O D S U M O W A N I E  P R O F I L U',
                'E D U C A T I O N': 'W Y K S Z T A Ł C E N I E',
                'L A N G U A G E S': 'J Ę Z Y K I',
                'C E R T I F I C A T I O N S': 'C E R T Y F I K A T Y',
                'P R O F I L E  S U M M A R Y': 'R E K O M E N D A C J A ',
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
            tr = header_table.rows[0]._tr
            trPr = tr.get_or_add_trPr()
            trHeight = OxmlElement('w:trHeight')
            trHeight.set(qn('w:val'), '900')  # ok. 1,8 cm; zwiększ do 1000–1200 jeśli chcesz więcej
            trHeight.set(qn('w:hRule'), 'atLeast')
            trPr.append(trHeight)
            # Szerokość i marginesy tabeli (jak było)
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

            # Niebieskie tło dla całego prostokąta
            header_cell = header_table.rows[0].cells[0]
            shading_elm = parse_xml(
                r'<w:shd {} w:fill="3282B4"/>'.format(
                    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
                )
            )
            header_cell._element.get_or_add_tcPr().append(shading_elm)

            # Wewnątrz tej niebieskiej komórki robimy 2 kolumny: [LOGO][TEKST]
            inner_table = header_cell.add_table(rows=1, cols=2)
            inner_table.autofit = False

            logo_cell = inner_table.rows[0].cells[0]
            text_cell = inner_table.rows[0].cells[1]

            logo_cell.width = Inches(2.3)
            text_cell.width = Inches(5.2)

            # Usuwamy bordery wewnętrznej tabeli, żeby był czysty prostokąt
            for cell in (logo_cell, text_cell):
                tcPr = cell._element.get_or_add_tcPr()
                tcBorders = OxmlElement('w:tcBorders')
                for border_name in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
                    border = OxmlElement(f'w:{border_name}')
                    border.set(qn('w:val'), 'none')
                    border.set(qn('w:sz'), '0')
                    border.set(qn('w:space'), '0')
                    border.set(qn('w:color'), 'auto')
                    tcBorders.append(border)
                tcPr.append(tcBorders)

            # LOGO – trochę wyżej
            logo_para = logo_cell.paragraphs[0]
            logo_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            logo_para.paragraph_format.space_before = Pt(0)  # mniejsza / ujemna wartość = wyżej
            logo_para.paragraph_format.space_after = Pt(0)
            logo_para.paragraph_format.left_indent = Inches(0.3)

            logo_path = r'C:\Users\Kamil Czyżewski\OneDrive - Integral Solutions sp. z o.o\Pulpit\Projects\HR_CV_Analyzer\IS_New.png'
            try:
                logo_run = logo_para.add_run()
                logo_run.add_picture(logo_path, width=Inches(2.0))
            except Exception as e:
                print(f'❌ Logo error in DOCX: {e}')

            # TEKST (imię + stanowisko) – trochę wyżej
            text_para = text_cell.paragraphs[0]
            text_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            text_para.paragraph_format.space_before = Pt(2)
            text_para.paragraph_format.space_after = Pt(0)

            name_run = text_para.add_run(candidate_name)
            apply_arsenal_font(name_run, size=28, bold=True)
            name_run.font.color.rgb = RGBColor(255, 255, 255)

            title_para = text_cell.add_paragraph()
            title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            title_para.paragraph_format.space_before = Pt(0)
            title_para.paragraph_format.space_after = Pt(2)  # było 10

            title_run = title_para.add_run(candidate_title)
            apply_arsenal_font(title_run, size=13, bold=False)
            title_run.font.color.rgb = RGBColor(255, 255, 255)
            # bottom_para = header_cell.add_paragraph()
            # bottom_para.paragraph_format.space_before = Pt(4)
            # bottom_para.paragraph_format.space_after = Pt(0)
        
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
        
        profile_summary = filtered_analysis.get("podsumowanie_profilu") or filtered_analysis.get("profile_summary") or ""
        
        if profile_summary and not filtered_analysis.get("mocne_strony"):
            highlights = [h.strip() for h in profile_summary.split('•') if h.strip()]
            
            if not highlights:
                sentences = re.split(r'\.\s+(?=[A-Z])', profile_summary)
                highlights = []
                for s in sentences:
                    s = s.strip()
                    if len(s) > 10:
                        if not s.endswith('.'):
                            s = s + '.'
                        highlights.append(s)
                    if len(highlights) >= 6:
                        break
            
            filtered_analysis['mocne_strony'] = highlights[:6]
        
        if not highlights or len(highlights) == 0:
            profile_text = filtered_analysis.get("podsumowanie_profilu") or filtered_analysis.get("profile_summary") or ""
            if profile_text and profile_text.strip():
                if "•" in profile_text:
                    highlights = [h.strip() for h in profile_text.split("•") if h.strip()][:6]
                else:
                    sentences = re.split(r'\.\s+(?=[A-Z])', profile_text)
                    highlights = []
                    for s in sentences:
                        s = s.strip()
                        if len(s) > 10:
                            if not s.endswith('.'):
                                s = s + '.'
                            highlights.append(s)
                        if len(highlights) >= 6:
                            break
        
        # PAGE 1 - KEY HIGHLIGHTS WITH UNDERLINE
        heading = doc.add_paragraph()
        run = heading.add_run(get_section_name('K E Y  H I G H L I G H T S'))
        apply_arsenal_font(run, size=13, bold=True)
        
        pPr = heading._element.get_or_add_pPr()
        pBdr = parse_xml(r'<w:pBdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:bottom w:val="single" w:sz="12" w:space="1" w:color="4C4C4C"/></w:pBdr>')
        pPr.append(pBdr)
        
        if highlights:
            for highlight in highlights:
                highlight_text = safe_text(highlight).strip()
                if highlight_text:
                    # Dodaj highlight jako paragraf z bulletem
                    p = doc.add_paragraph()
                    p.paragraph_format.space_before = Pt(0)
                    p.paragraph_format.space_after = Pt(0)
                    
                    # Split into words and add with bold for keywords
                    words = highlight_text.split()
                    for i, word in enumerate(words):
                        if i == 0:
                            # First word gets bullet
                            run = p.add_run('• ' + word)
                        else:
                            run = p.add_run(' ' + word)
                        
                        word_lower = word.lower().strip('.,;:!?()"\'')
                        has_keyword = any(kw.lower() in word_lower for kw in keywords) if keywords else False
                        
                        run.font.name = 'Arsenal'
                        run.font.size = Pt(11)
                        run.bold = has_keyword
        
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
        
        # SKILLS WITH UNDERLINE
        heading = left_cell.add_paragraph()
        run = heading.add_run(get_section_name('S K I L L S'))
        apply_arsenal_font(run, size=10, bold=True)

        # ✅ DODAJ UNDERLINE:
        pPr = heading._element.get_or_add_pPr()
        pBdr = parse_xml(r'<w:pBdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:bottom w:val="single" w:sz="12" w:space="1" w:color="4C4C4C"/></w:pBdr>')
        pPr.append(pBdr)
        
        skills_data = filtered_analysis.get("umiejetnosci") or filtered_analysis.get("skills")
        if skills_data:
            skill_cats = [
                ('programowanie_skrypty', 'programming_scripting', 'Programming'),
                ('frameworki_biblioteki', 'frameworks_libraries', 'Frameworks'),
                ('mobile', 'mobile', 'Mobile'),
                ('infrastruktura_devops', 'infrastructure_devops', 'Infrastructure'),
                ('chmura', 'cloud', 'Cloud'),
                ('bazy_kolejki', 'databases_messaging', 'Data'),
                ('monitoring', 'monitoring', 'Monitoring'),
                ('inne', 'other', 'Other'),
            ]
            
            for pl_key, en_key, label in skill_cats:
                skills_list = skills_data.get(pl_key) or skills_data.get(en_key)
                if skills_list:
                    skills_str = ', '.join([safe_text(s) for s in skills_list])
                    


                    # Label - bold
                    p = left_cell.add_paragraph(f"{label}:")
                    p.paragraph_format.space_before = Pt(8)
                    p.paragraph_format.space_after = Pt(4)
                    for run in p.runs:
                        apply_arsenal_font(run, size=9, bold=True)
                    
                    # Technologies - with BOLD keywords
                    self._add_paragraph_with_bold_keywords(left_cell, skills_str, keywords, base_size=9)

        
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
                    apply_arsenal_font(run, size=9, bold=False)
        
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
                    apply_arsenal_font(run, size=9, bold=False)
        
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
                    apply_arsenal_font(run, size=9, bold=True)
                
                p = left_cell.add_paragraph(issuer)
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                for run in p.runs:
                    apply_arsenal_font(run, size=9, bold=False)
        
        # ===== RIGHT COLUMN =====
        
        # PROFILE SUMMARY WITH UNDERLINE
        add_section_header_with_underline(right_cell, get_section_name('P R O F I L E  S U M M A R Y'))
        
        if profile_summary:
            profile_text = safe_text(profile_summary).replace('•', '').strip()
            self._add_paragraph_with_bold_keywords(right_cell, profile_text, keywords, base_size=9)
        
        # WORK EXPERIENCE WITH UNDERLINE
        p = right_cell.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(0)
        add_section_header_with_underline(right_cell, get_section_name('W O R K  E X P E R I E N C E'))

        #tu
        if work_exp_data:
            for idx, exp in enumerate(work_exp_data):
                period = safe_text(exp.get('okres') or exp.get('period', ''))
                company = safe_text(exp.get('firma') or exp.get('company', ''))
                position = safe_text(exp.get('stanowisko') or exp.get('position', ''))
                achievements = exp.get('kluczowe_osiagniecia') or exp.get('key_achievements', [])

                # odstęp między jobami
                if idx > 0:
                    spacer = right_cell.add_paragraph()
                    spacer.paragraph_format.space_before = Pt(4)
                    spacer.paragraph_format.space_after = Pt(0)

                # 1. Stanowisko – bold, większy font
                if position:
                    p_pos = right_cell.add_paragraph()
                    p_pos.paragraph_format.space_before = Pt(0)
                    p_pos.paragraph_format.space_after = Pt(0)
                    run_pos = p_pos.add_run(position)
                    apply_arsenal_font(run_pos, size=10, bold=True)

                # 2. Okres – bold
                if period:
                    p_period = right_cell.add_paragraph()
                    p_period.paragraph_format.space_before = Pt(0)
                    p_period.paragraph_format.space_after = Pt(0)
                    run_period = p_period.add_run(period)
                    apply_arsenal_font(run_period, size=9, bold=True)

                # 3. Firma – bold
                if company:
                    p_company = right_cell.add_paragraph()
                    p_company.paragraph_format.space_before = Pt(0)
                    p_company.paragraph_format.space_after = Pt(2)
                    run_company = p_company.add_run(company)
                    apply_arsenal_font(run_company, size=9, bold=True)

                # 4. Zadania – font 9, bez bold
                if achievements:
                    for achievement in achievements:
                        self._add_paragraph_with_bold_keywords(
                            right_cell,
                            safe_text(achievement),
                            keywords,
                            base_size=9,
                            space_before=0,
                            space_after=2,
                            bold_base=False
                        )
        
        # EDUCATION WITH UNDERLINE
        p = right_cell.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(0)
        add_section_header_with_underline(right_cell, get_section_name('E D U C A T I O N'))
        
        education_data = filtered_analysis.get('wyksztalcenie') or filtered_analysis.get('education', [])



        if education_data and len(education_data) > 0:
            
            for edu in education_data:
                institution = safe_text(edu.get('uczelnia') or edu.get('institution'), '')
                degree = safe_text(edu.get('stopien') or edu.get('degree'), '')
                field = safe_text(edu.get('kierunek') or edu.get('field_of_study') or edu.get('field'), '')
                period = safe_text(edu.get('okres') or edu.get('period'), '')
                
                # ✅ RENDERUJ TYLKO JEŚLI DANE ISTNIEJĄ (jak w PDF!)
                if institution and institution not in ['', 'None', 'N/A']:
                    p = right_cell.add_paragraph(institution)
                    apply_arsenal_font(p.runs[0], size=9, bold=False)
                
                if degree or field:
                    degree_field = f"{degree} of {field}" if degree and field else (degree or field)
                    if degree_field and degree_field not in ['', 'None', 'N/A', ' of ']:
                        p = right_cell.add_paragraph(degree_field)
                        apply_arsenal_font(p.runs[0], size=9, bold=False)
                
                if period and period not in ['', 'None', 'N/A']:
                    p = right_cell.add_paragraph(period)
                    apply_arsenal_font(p.runs[0], size=9, bold=False)
        
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer