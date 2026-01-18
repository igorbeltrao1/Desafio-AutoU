# Copilot Instructions - Email Classifier

## Project Overview

**Email Classifier with AI-Powered Responses** - A Flask web application that classifies emails into two categories (Productive/Improdutive) and auto-generates contextual responses using Hugging Face inference API.

### Architecture

```
app.py (main Flask app)
├── Frontend: HTML form with text/file upload (templates/index.html)
├── File Extraction: PDF/TXT parser (extrairTextoPdf, extrairTextoTxt)
├── Classification Pipeline: Dual-mode system
│   ├── Mode 1: IA-based (Hugging Face API with fallback)
│   └── Mode 2: Hybrid scoring (keyword detection + context analysis)
└── Response Generation: Context-aware automatic replies
```

## Key Patterns & Conventions

### Classification System (Dual-Mode)

1. **IA Classification** (`classificarEmailComIa`):
   - Tries 2 updated models (Jan 2026): `microsoft/Phi-3-mini-4k-instruct`, `tiiuae/falcon-7b-instruct`
   - Falls back to hybrid scoring if API fails (410, 503 errors)
   - Timeout: 20s per request

2. **Hybrid Scoring** (`classificarHibrido`):
   - Keyword-based scoring system with 3 tiers per category:
     - **Very Strong** (weight: 10): "solicito", "protocolo", "chamado"
     - **Strong** (weight: 5): "status", "problema", "urgente"
     - **Medium** (weight: 2): "dúvida", "preciso", "gostaria"
   - Contextual modifiers: text length, line count, punctuation patterns
   - Final comparison: `scoreProdutivo > scoreImprodutivo`

### Response Generation (`gerarRespostaAutomatica`)

- **Productive emails**: Formal professional tone, structured format, addresses action items
- **Improdutive emails**: Warm, personal tone, acknowledges sentiment
- Models tested in sequence (4 options with 30s timeout each)
- Falls back to contextual template generation if all models fail

### Response Validation & Cleanup

- `validarRespostaIa`: Checks min length (30 chars), semantic relevance, greeting/closing presence
- `limparRespostaIaAvancado`: Strips prompt artifacts, normalizes whitespace, removes markers
- `gerarRespostaContextual`: Template-based fallback with regex extraction (protocol #, names)

## File Structure & Responsibilities

| File | Purpose |
|------|---------|
| `app.py` | Core Flask app + all processing logic (594 lines) |
| `templates/index.html` | Tab-based UI (text/file upload, results display) |
| `static/style.css` | Responsive design with gradient background |
| `requirements.txt` | Dependencies: Flask, PyPDF2, transformers, torch, etc. |
| `.env` | `HUGGINGFACE_API_KEY` (required for operation) |

## Critical Developer Workflows

### Setup & Run
```bash
# Configure environment
echo "HUGGINGFACE_API_KEY=hf_xxxxx" > .env

# Install dependencies
pip install -r requirements.txt

# Run server
python app.py  # Runs on http://localhost:5000
```

### Deployment Considerations

- **Model Availability**: Hugging Face API models are versioned (Jan 2026 snapshot). Handle 410 "Gone" responses gracefully
- **Memory**: Transformers + PyTorch are heavy; ensure 4GB+ RAM for local inference
- **Timeouts**: API requests timeout at 20-30s; consider async processing for production
- **File Upload**: Max 10MB (`MAX_FILE_SIZE = 10 * 1024 * 1024`), allowed extensions: `.txt`, `.pdf`

## External Dependencies & Integration Points

- **Hugging Face Inference API**: `https://api-inference.huggingface.co/models/`
  - Auth: Bearer token from `HF_API_KEY`
  - Fallback models for robustness
  - Handles model loading/unloading (503 "Model Loading" responses)
  
- **PyPDF2**: PDF text extraction with error handling for corrupted files
- **Flask**: Lightweight WSGI, uses Werkzeug for file validation

## Testing & Debugging

### Key Entry Points
1. `@app.route('/classificar', methods=['POST'])`: Main endpoint, handles text & file inputs
2. `classificarEmailComIa()`: Try setting breakpoint here to debug model response parsing
3. `classificarHibrido()`: Check keyword matching logic with print statements (already verbose)

### Debug Output
- Console prints detailed classification scores: `📊 SCORE FINAL: Produtivo=X, Improdutivo=Y`
- Model attempts are logged: `[Tentativa i/N] Modelo: ...`
- API errors include status codes: `Status: 410`, `Status: 503`

## Common Pitfalls & Edge Cases

1. **Missing API Key**: App still runs but classification fails gracefully → falls back to hybrid
2. **Encoding Issues**: TXT files try UTF-8 first, then latin-1 fallback
3. **Empty Extraction**: Returns 400 error; validation checks `len(texto) < 10`
4. **Model Timeout**: Retries next model in list automatically (no manual restart needed)
5. **Overlapping Keywords**: Scoring is cumulative; context matters (e.g., "não funciona" + "problema" = 5+5 points)

## Code Style Notes

- Portuguese variable/function names (e.g., `extrairTextoTxt`, `classificarHibrido`)
- Extensive print logging with emoji indicators (✅, ❌, ⚠️, 📊, 🤖, etc.)
- Email validation via keyword lists (no ML tokenizer for offline mode)
- Response templates include fallback for contextual extraction (`re.search` for protocol #, names)
