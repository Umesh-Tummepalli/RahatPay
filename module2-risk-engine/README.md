## Module 2 — AI Risk Engine & Premium Calculator

### Setup
pip install -r requirements.txt

### Run training
python training/build_dataset.py
python training/train_model.py

### Run tests
python -m pytest tests/ -v

### Start server
uvicorn main:app --reload --port 8002