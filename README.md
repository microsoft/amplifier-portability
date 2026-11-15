# Amplifier Portability

Python tools for moving selected work between explicitly paired hosts. The
library provides signed transfer receipts, workspace capsules, and verified
copies of selected historical data.

It is intended for applications implementing a reviewed handoff. The application
still controls host authentication, transport, user approval, and which runtime is
allowed to continue the work.

## Get started

Use Python 3.11 or later. From a checkout, install the package and its dependencies
in a virtual environment:

```sh
uv venv
uv pip install .
```

Create a durable local identity and receipt store in a private directory owned by
your application:

```python
from amplifier_portability import TransferNode

node = TransferNode('./.portability', label='my-host')
print(node.identity['id'])
```

Keep that directory private and persistent: it holds the host's signing key and
transfer records. Creating a node does not pair hosts, move files, or start an
agent. Follow the [transfer contract](docs/contract.v1.md) when connecting the
library to your application's trusted pairing and runtime controls.

## Choose the part you need

- `TransferNode`: signed handoff records and queries for their current state.
- [Workspace capsules](src/amplifier_portability/capsule.py): capture and restore
  reviewed workspace changes against an exact source revision.
- [Owner evidence](src/amplifier_portability/evidence.py): preserve exact JSON
  bytes and explicit omissions across a transfer.
- [Historical payloads](docs/payload-contract.v1.md): copy selected attachment or
  resource bodies with size and digest verification.

Treat a capsule as data, not permission to execute its contents. Secret-pattern
checks cannot prove that arbitrary content is safe to share; review what you send. A missing or uncertain receipt must be inspected, not treated as
permission to repeat the transfer.

## Development

```sh
uv sync --group dev
uv run pytest
uv build
```

See the [integration contract](docs/contract.v1.md) for API responsibilities and
supported boundaries.

## Contributing

Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
