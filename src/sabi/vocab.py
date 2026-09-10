"""SABI capability vocabulary (v0.1).

Canonical capability identifiers grouped into the nine families:
filesystem, process/shell, web/network, git/repository, database,
test/ci, artifact/deployment, message, user/agent.
"""

VOCAB = {
    # filesystem
    "filesystem.read", "filesystem.write", "filesystem.search",
    # process / shell
    "shell.execute", "process.execute",
    # web / network
    "web.search", "web.fetch", "browser.navigate",
    "network.fetch", "network.search", "network.egress",
    # git / repository
    "git.read", "git.write",
    "repository.read", "repository.search", "repository.change",
    "repository.write", "repository.patch", "repository.merge",
    # database
    "database.read", "database.write",
    # test / ci
    "ci.execute", "test.execute",
    # artifact / deployment
    "deployment.create", "artifact.create",
    # message
    "message.send",
    # user / agent
    "user.interact", "agent.delegate",
}

FAMILIES = {
    "filesystem": ("filesystem.read", "filesystem.write", "filesystem.search"),
    "process": ("shell.execute", "process.execute"),
    "web": ("web.search", "web.fetch", "browser.navigate",
            "network.fetch", "network.search", "network.egress"),
    "repository": ("git.read", "git.write", "repository.read",
                   "repository.search", "repository.change",
                   "repository.write", "repository.patch", "repository.merge"),
    "database": ("database.read", "database.write"),
    "ci": ("ci.execute", "test.execute"),
    "artifact": ("deployment.create", "artifact.create"),
    "message": ("message.send",),
    "user": ("user.interact", "agent.delegate"),
}


def is_known(capability):
    """True when *capability* is in the SABI vocabulary."""
    return capability in VOCAB


def unknown(caps):
    """Return the sorted list of capabilities not in the vocabulary."""
    return sorted({c for c in caps if c not in VOCAB})