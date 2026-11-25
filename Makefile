.PHONY: up down test data train lint
up:        ## build and start UI (http://localhost:8080) + API (http://localhost:8000/docs)
	docker compose up --build -d
down:
	docker compose down
test:      ## backend + ML pipeline tests
	cd backend && python -m pytest -q
	python -m pytest ml/tests -q
data:      ## rebuild data/model_table.csv from the raw workbook
	python ml/data_prep.py data/raw/LT_Interview_Exercise_Head_of_AI.xlsx data
train:     ## retrain, evaluate and export models/ + reports/
	python ml/train.py data/model_table.csv models reports
