## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd "Browser Query AI Orchestration"
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   ```

3. **Activate the virtual environment:**

    On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```


4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Project

After installation, make sure your virtual environment is activated, then run:

```bash
# Make sure venv is activated (you should see (venv) in your terminal)
uvicorn app.main:app --reload --port 8000
```

**Important:** Always activate the virtual environment before running the project:
```bash
source venv/bin/activate  # On macOS/Linux
```
