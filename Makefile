.PHONY: install-crds uninstall-crds example run lint test

install-crds:
	kubectl apply -f examples/tenant-crd.yml

uninstall-crds:
	kubectl delete -f examples/tenant-crd.yml --ignore-not-found

example:
	kubectl apply -f examples/tenant-example.yml

run:
	TIERS_CONFIG=deploy/tiers.json kopf run python/src/main.py --verbose -A

lint:
	pre-commit run --all-files

test:
	pytest python/tests/unit -v
