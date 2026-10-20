from typing import Any

import kopf
from kubernetes import client

from const import (
    DNS_NAMESPACE,
    DNS_POD,
    NAMESPACE_NAME_LABEL,
    NETWORK_POLICY_NAME,
    TENANT_LABEL,
)
from k8s import create_or_patch, networking


def ensure(
    ns: str,
    spec: kopf.Spec,
    logger: kopf.Logger,
    tenant: str,
) -> None:
    """Create or patch the tenant's Network Policy from spec.network.

    Safe to call repeatedly. Manages one policy, tenant-network, covering every pod.

    Ingress: only pods in the same namespace, plus the spec's ingress rules.
    Egress: open by default. If spec.network.egress is set, only the same namespace,
    cluster DNS and the listed rules are allowed.
    """
    same_ns = client.V1NetworkPolicyPeer(pod_selector=client.V1LabelSelector())
    network = spec.get("network", {})

    ingress = [client.V1NetworkPolicyIngressRule(_from=[same_ns])]
    ingress += [_ingress_rule(r) for r in network.get("ingress", [])]

    policy_types = ["Ingress"]
    egress = None
    egress_spec = network.get("egress", [])
    if egress_spec:
        policy_types.append("Egress")
        egress = [client.V1NetworkPolicyEgressRule(to=[same_ns]), _dns_rule()]
        egress += [_egress_rule(r) for r in egress_spec]

    policy = client.V1NetworkPolicy(
        metadata=client.V1ObjectMeta(
            name=NETWORK_POLICY_NAME, labels={TENANT_LABEL: tenant}
        ),
        spec=client.V1NetworkPolicySpec(
            pod_selector=client.V1LabelSelector(),
            policy_types=policy_types,
            ingress=ingress,
            egress=egress,
        ),
    )

    create_or_patch(
        networking().create_namespaced_network_policy,
        networking().patch_namespaced_network_policy,
        NETWORK_POLICY_NAME,
        ns,
        policy,
        "NetworkPolicy",
        logger,
    )


def _peer(rule: dict[str, Any]) -> client.V1NetworkPolicyPeer:
    """Return the peer for a rule: a CIDR, or another tenant's namespace
    or a named namespace."""
    if "cidr" in rule:
        return client.V1NetworkPolicyPeer(ip_block=client.V1IPBlock(cidr=rule["cidr"]))
    if "namespace" in rule:
        return client.V1NetworkPolicyPeer(
            namespace_selector=client.V1LabelSelector(
                match_labels={NAMESPACE_NAME_LABEL: rule["namespace"]}
            )
        )
    return client.V1NetworkPolicyPeer(
        namespace_selector=client.V1LabelSelector(
            match_labels={NAMESPACE_NAME_LABEL: f"tenant-{rule['tenant']}"}
        )
    )


def _ports(rule: dict[str, Any]) -> list[client.V1NetworkPolicyPort]:
    """Return the rule's ports, defaulting the protocol to TCP."""
    return [
        client.V1NetworkPolicyPort(port=p["port"], protocol=p.get("protocol", "TCP"))
        for p in rule["ports"]
    ]


def _ingress_rule(rule: dict[str, Any]) -> client.V1NetworkPolicyIngressRule:
    """Return an ingress rule for each ingress entry."""
    return client.V1NetworkPolicyIngressRule(_from=[_peer(rule)], ports=_ports(rule))


def _egress_rule(rule: dict[str, Any]) -> client.V1NetworkPolicyEgressRule:
    """Return an egress rule for each egress entry."""
    return client.V1NetworkPolicyEgressRule(to=[_peer(rule)], ports=_ports(rule))


def _dns_rule() -> client.V1NetworkPolicyEgressRule:
    """Return an egress rule allowing DNS traffic to the cluster's CoreDNS pods."""
    dns = client.V1NetworkPolicyPeer(
        namespace_selector=client.V1LabelSelector(match_labels=DNS_NAMESPACE),
        pod_selector=client.V1LabelSelector(match_labels=DNS_POD),
    )
    return client.V1NetworkPolicyEgressRule(
        to=[dns],
        ports=[
            client.V1NetworkPolicyPort(port=53, protocol="UDP"),
            client.V1NetworkPolicyPort(port=53, protocol="TCP"),
        ],
    )
