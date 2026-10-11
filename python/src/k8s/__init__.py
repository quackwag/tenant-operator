from functools import cache

from kubernetes import client


@cache
def core() -> client.CoreV1Api:
    return client.CoreV1Api()


@cache
def networking() -> client.NetworkingV1Api:
    return client.NetworkingV1Api()


@cache
def rbac() -> client.RbacAuthorizationV1Api:
    return client.RbacAuthorizationV1Api()
