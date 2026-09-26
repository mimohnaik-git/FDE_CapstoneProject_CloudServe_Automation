.PHONY: setup data train test eval api demo

setup:
	python -m pip install -r requirements.txt

data:
	python -m scripts.make_sample_data

train:
	python -m scripts.train --input data/cloudserve/development_tickets.json

test:
	python -m pytest -q

eval:
	python -m evaluation.harness --input data/cloudserve/validation_tickets.json \
		--output evaluation/results/local_validation_run \
		--references data/cloudserve/ground_truth_responses.json \
		--reference-tickets data/cloudserve/development_tickets.json \
		--kb data/cloudserve/documentation.json \
		--retrieval-backend tfidf \
		--enable-auto-policy \
		--fail-on-must-not-auto

demo:
	python -m scripts.demo

api:
	python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
