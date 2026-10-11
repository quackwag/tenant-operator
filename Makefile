.PHONY: install-crds uninstall-crds example run lint test

install-crds:
	kubectl apply -f crds/

uninstall-crds:
	kubectl delete -f crds/ --ignore-not-found

example:
	kubectl apply -f examples/

run:
	kopf run python/src/main.py --verbose

lint:
	pre-commit run --all-files

test:
	pytest python/tests/
