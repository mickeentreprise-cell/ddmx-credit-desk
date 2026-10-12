# DDMX Credit Desk

Credit infrastructure for autonomous agents on BNB Chain.

**Deploy in one step:** the whole server is `ddmx_tout_en_un.py` — a
single Python file, no dependencies. `render.yaml` configures the host.
See [COMMENT-DEPLOYER.md](COMMENT-DEPLOYER.md).

## The problem

**339,581 agents are registered on ERC-8004 on BNB Chain** — more than any
other chain. Worldwide: **882,751**.

They have an identity. They have a reputation. **None of them has access
to credit.**

The ERC-8004 standard defines three registries: identity, reputation and
validation. It defines **no lending mechanism at all**. Verified by direct
call: `preter()`, `emprunter()`, `loan()`, `creditScore()`, `collateral()`
are **all absent** from the BNB Chain registries.

## What this service does

A credit desk for agents, payable over **x402** — the HTTP 402 payment
standard, now a Linux Foundation project.

An agent:

1. **Discovers** the service — `/.well-known/agent-card.json` (A2A card)
2. **Talks** to it — `POST /a2a` with JSON-RPC
3. **Pays** — `GET /registre` returns HTTP 402, the agent pays on-chain
4. **Receives** — the server reads the payment event and responds

No account. No API key. No KYC. No email.

## The three paid resources

| Resource | Price | What it returns |
|---|---|---|
| `GET /registre` | 5.00 USDC | Register an agent in the verified registry |
| `GET /score` | 2.00 USDC | Publish an on-chain reputation report |
| `GET /conseil` | 25.00 USDC | Credit file analysis |

Two **free** A2A skills for discovery: `evaluer-credit` and
`expliquer-garantie`.

## The rule that makes the score meaningful

> **An agent cannot confirm its own work.**
> **Neither can its owner.**
> **Only a distinct client can.**

This is enforced **in the contract**, not in a policy document. Without
it, an agent could vouch for itself ten thousand times and borrow against
nothing.

## Why the lender cannot lose

The borrower deposits **150 % collateral BEFORE any capital moves**.

A constant-product pool never returns more than it holds. Same logic here:
the guarantee is inside the contract before the first token leaves it.

## Contracts — all verified on BscScan

| Contract | Address |
|---|---|
| DDMX token | [`0x90e28b1c…6b53`](https://bscscan.com/token/0x90e28b1c8f1534dd3dc1c5ce9475fb5737d46b53) |
| Agent registry | [`0x39d545b8…9c23`](https://bscscan.com/address/0x39d545b828beca7e870810d6eb480364ed8c9c23#code) |
| Credit oracle | [`0xaac78b28…d8f7`](https://bscscan.com/address/0xaac78b28f8302cdd57a0bfd394819b779c77d8f7#code) |
| Credit market | [`0x6b4d9c88…521d`](https://bscscan.com/address/0x6b4d9c88a8a1c599bce9e510739d82afd04b521d#code) |
| Agent credit market | [`0xf4d29a1a…fa6f`](https://bscscan.com/address/0xf4d29a1aea231cd684d6550fe11717dc67e5fa6f#code) |
| Multisig vault | [`0xd38a1aec…92ec`](https://bscscan.com/address/0xd38a1aec4fd48d26cf201e820c305cddd60092ec#code) |
| x402 gateway | [`0x490a9397…d655`](https://bscscan.com/address/0x490a9397d1e79dd0186771f162bf065da3d3d655) |

**The source code is public. Read it.**

## Run locally

```bash
pip install -r requirements.txt
python -u serveur_x402.py
```

Then open http://127.0.0.1:8098/

## Deploy

**Render** reads `render.yaml` automatically.
**Railway** reads `railway.json` automatically.
**Docker** works with the included `Dockerfile`.

### Environment variables

| Variable | Default | What it does |
|---|---|---|
| `PORT` | `8098` | imposed by the host |
| `X402_ECOUTE` | `0.0.0.0` | listen address |
| `X402_URL` | *(empty)* | public URL, if set |

**Without `X402_URL`, the server reads the `Host` header of each request.**
That works in most cases. Set `X402_URL` if your host rewrites headers.

## One caveat, stated plainly

**BNB Chain is not covered by the x402.org facilitator**, which currently
lists only testnets (Base Sepolia, Solana devnet, Algorand, Aptos,
Stellar, Hedera, XRPL).

This is not a blocker: **x402 requires no facilitator.** The protocol is
open, and the server verifies payment itself. Our `X402Gateway` contract
plays that role and emits a verifiable receipt.

## What this service does NOT do

- ❌ Promises no return, no yield, no price
- ❌ Holds no third-party funds — payments go straight to the beneficiary
- ❌ Provides no investment advice
- ❌ Has no external audit *(the contracts are verified and readable by anyone)*

## Legal

Crypto Future Tech — sole proprietorship, unlimited liability
Geneva, Switzerland — CH-660.6.918.025-9

**No FINMA authorisation is required for this service**: there is no
public deposit-taking, no third-party fund management, and no promise of
return. The contracts are public and verifiable.

## Licence

MIT
