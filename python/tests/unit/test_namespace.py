from unittest.mock import MagicMock

import kopf
import pytest
from kubernetes import client
from kubernetes.client.exceptions import ApiException

from const import TENANT_LABEL
from k8s import namespace

TENANT_UID = "uid-123"


@pytest.fixture
def body():
    """A minimal Tenant, as kopf would pass it to the handler."""
    return {
        "apiVersion": "platform.tenancy.io/v1alpha1",
        "kind": "Tenant",
        "metadata": {"name": "payments", "uid": TENANT_UID},
    }


@pytest.fixture
def fake_core(monkeypatch):
    """Replace the real CoreV1Api with a fake that records every call."""
    fake = MagicMock()
    monkeypatch.setattr(namespace, "core", lambda: fake)
    return fake


def existing_ns(owner_uid, labels):
    """Build the namespace object read_namespace would return."""
    refs = [
        client.V1OwnerReference(
            api_version="v1", kind="Tenant", name="payments", uid=owner_uid
        )
    ]
    return client.V1Namespace(
        metadata=client.V1ObjectMeta(
            name="tenant-payments", labels=labels, owner_references=refs
        )
    )


def test_creates_namespace(body, fake_core):
    name = namespace.ensure(body, MagicMock())

    assert name == "tenant-payments"
    fake_core.create_namespace.assert_called_once()
    ns = fake_core.create_namespace.call_args.kwargs["body"]
    assert ns.metadata.labels == {TENANT_LABEL: "payments"}
    assert ns.metadata.owner_references[0].uid == TENANT_UID


def test_not_ours_raises(body, fake_core):
    fake_core.create_namespace.side_effect = ApiException(status=409)
    fake_core.read_namespace.return_value = existing_ns("someone-else", {})

    with pytest.raises(kopf.PermanentError):
        namespace.ensure(body, MagicMock())


# test_ours_with_label_does_nothing()

# test_ours_missing_label_patches()
