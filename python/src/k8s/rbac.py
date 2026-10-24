import kopf
from kubernetes import client

from const import BINDING_ROLE_MAP, BINDING_ROLE_NAME, TENANT_LABEL
from k8s import create_or_patch, rbac_api


def ensure(
    ns: str,
    spec: kopf.Spec,
    logger: kopf.Logger,
    tenant: str,
) -> None:
    """Create or patch the tenant's RoleBindings from spec owners, members and viewers.

    Safe to call repeatedly. Manages one RoleBinding per access level, each pointing at
    a built in ClusterRole and scoped to the tenant's namespace.

    A binding is always created, even with no subjects, so removing the last subject from
    a list removes their acess."""
    for group, role in BINDING_ROLE_MAP.items():
        name = f"{BINDING_ROLE_NAME}-{group}"
        subjects = _subjects(spec.get(group, []))

        role_binding = client.V1RoleBinding(
            metadata=client.V1ObjectMeta(name=name, labels={TENANT_LABEL: tenant}),
            role_ref=client.V1RoleRef(
                kind="ClusterRole", name=role, api_group="rbac.authorization.k8s.io"
            ),
            subjects=subjects,
        )

        create_or_patch(
            rbac_api().create_namespaced_role_binding,
            rbac_api().patch_namespaced_role_binding,
            name,
            ns,
            role_binding,
            "RoleBinding",
            logger,
        )


def _subjects(emails: list[str]) -> list[client.RbacV1Subject]:
    """Return one User subject per email."""
    return [
        client.RbacV1Subject(
            api_group="rbac.authorization.k8s.io", kind="User", name=email
        )
        for email in emails
    ]
