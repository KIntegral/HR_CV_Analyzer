# 🤖 HR CV Analyzer - AI-Powered Recruitment Assistant

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**AI-powered CV analysis tool for HR professionals** that automatically extracts, analyzes, and matches candidate profiles against job requirements using local LLMs.

![Screenshot](screenshot.png)

---

## 📋 Table of Contents

- [Features](#features)
- [Technologies](#technologies)
- [Installation](#installation)
- [Usage](#usage)
- [Template Types](#template-types)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)

---

## ✨ Features

### Core Functionality
- 📄 **Multi-format Support**: PDF, DOCX, DOC, JPG, PNG
- 🌍 **Bilingual**: Polish and English interface & analysis
- 🔄 **Auto Translation**: Analyze Polish CV → English report (and vice versa)
- 🤖 **Local LLM**: Privacy-first using Ollama (offline capability)
- 📊 **Smart Matching**: AI-powered candidate-to-requirement matching

### Analysis Capabilities
- 👤 Basic information extraction
- 📍 Location & availability preferences
- 💼 Work experience with detailed project breakdowns
- 🎓 Education & certifications
- 🛠️ Technology stack identification
- 💪 Key strengths mapping to requirements
- 📈 Match level scoring with recommendations

### Output Options
- **Template Types**: Full, Short, Anonymous, Extended
- **Export Formats**: PDF, DOCX, JSON
- **AI Assistant**: Text correction, content generation

---

## 🛠️ Technologies

### Core Stack
- **Python 3.8+**
- **Streamlit** - Web UI framework
- **Ollama** - Local LLM inference
- **ReportLab** - PDF generation
- **python-docx** - DOCX generation

### AI Models (Recommended)
- **Qwen2.5 14B** - Best for multilingual CV analysis
- **Llama 3.1 8B** - Balanced performance
- **Mistral 7B** - Lightweight option

### Document Processing
- **PyMuPDF** - PDF text extraction
- **Pillow** - Image processing
- **Tesseract OCR** - Image-to-text conversion

---

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- Ollama installed ([download here](https://ollama.ai/))
- Tesseract OCR ([download here](https://github.com/UB-Mannheim/tesseract/wiki))

### Step 1: Clone Repository

git clone https://github.com/yourusername/hr-cv-analyzer.git
cd hr-cv-analyzer

### Step 2: Install Python Dependencies
pip install streamlit pymupdf pillow pytesseract ollama python-docx reportlab

Or use requirements.txt:

pip install -r requirements.txt

### Step 3: Install Ollama Model

ollama pull qwen2.5:14b

Or use a lighter model:

ollama pull llama3.1:8b

### Step 4: Configure Tesseract (Windows)
Add Tesseract to your PATH or set in `cv_analyzer_backend.py`:

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

---

## 🚀 Usage

### Start the Application
streamlit run streamlit_app.py

The app will open at `http://localhost:8501`

### Basic Workflow

1. **Upload CV** - Drop or select PDF/DOCX/Image file
2. **Enter Requirements** - Describe job requirements
3. **Configure**:
   - Select LLM model
   - Choose output language
   - Pick template type
4. **Analyze** - Click "Analyze CV"
5. **Download** - Get PDF/DOCX/JSON report

### Advanced Features

#### AI Text Assistant
- Spell checking and grammar correction
- Generate job descriptions from tech stack
- Create candidate summaries
- Custom text transformations

#### Custom Prompts
Enable "Advanced" to write custom analysis prompts.

---

## 📋 Template Types

| Template | Description | Use Case |
|----------|-------------|----------|
| **Full** | Complete analysis with all data | Standard recruitment process |
| **Short** | Top 3 experiences, 5 key skills | Quick screening |
| **Anonymous** | Hidden personal data & company names | Blind recruitment, GDPR compliance |
| **Extended** | Full + interview questions + recommendations | Senior positions, detailed assessment |

---

## ⚙️ Configuration

### Sidebar Options

**Model Selection**:
- qwen2.5:14b (Recommended)
- llama3.1:8b
- deepseek-r1:8b
- mistral:7b

**Output Language**:
- Auto (same as CV)
- Polish
- English

**Output Format**:
- PDF
- DOCX
- JSON

---

## 📁 Project Structure

HR_CV_Analyzer/
├── streamlit_app.py # Main Streamlit UI
├── cv_analyzer_backend.py # Core analysis logic
├── .gitignore
├── README.md
├── requirements.txt
└── screenshots/
└── screenshot.png

text

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Kamil Czyżewski**
- 🏢 Data Science Consultant @ Integral Solutions
- 📧 [czyzewskikamil01@gmail.com](mailto:czyzewskikamil01@gmail.com)
- 💼 [LinkedIn](https://linkedin.com/in/kamil-czyzewski)

---

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai/) - Local LLM runtime
- [Streamlit](https://streamlit.io/) - Beautiful UI framework
- [ReportLab](https://www.reportlab.com/) - PDF generation
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - OCR engine

---

## 📊 Roadmap

- [ ] Batch CV processing
- [ ] Database integration (PostgreSQL)
- [ ] Resume quality scoring
- [ ] API endpoint for integration
- [ ] Docker containerization
- [ ] Advanced analytics dashboard

---

