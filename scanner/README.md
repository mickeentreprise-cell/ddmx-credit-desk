# BEP-20 Token Scanner

**A free tool that checks a BEP-20 token before you buy it.**

🔗 **Live: https://mickeentreprise-cell.github.io/ddmx-credit-desk/**

No account. No installation. No server. No data leaves your browser.

---

## What it does

Paste a token address. It reads the contract directly from BNB Chain and
tells you what it can see:

| Check | What it looks for |
|---|---|
| **Owner** | Is there an `owner()` function? Can someone control the token? |
| **Pause** | Can someone freeze all transfers? |
| **Blacklist** | Can someone block your wallet from selling? |
| **Mint** | Can the supply be increased, diluting your share? |
| **Tax** | *(reported honestly as UNKNOWN — see below)* |
| **Code size** | Is the contract bigger than a normal token? Is something hidden? |

Then it gives a verdict and a score out of 10.

---

## What it does NOT do

**This scanner does not prove anything.**

- It reads what is **readable on-chain**. Nothing more.
- **The tax is not measurable this way.** Tax is measured by simulating a
  buy and a sell. A static scan cannot see it. The tool says so instead of
  guessing.
- A contract can hide a mechanism this analysis does not detect.
- **The only complete verification is reading the source code on BscScan.**

The tool states these limits on every result. That is deliberate.

---

## Why it exists

Most token scanners tell you a token is "safe" and give it a green score.

That is not honest. A green score implies a guarantee the tool cannot give.

This one shows the checks it ran, the evidence behind each one, and the
things it cannot check. If it says UNKNOWN, it means UNKNOWN.

---

## How it works

Single HTML file. No build step. No dependencies. No framework.

- Calls public BNB Chain RPC nodes over standard JSON-RPC (`eth_call`,
  `eth_getCode`)
- Tries four nodes in order, falls back on failure
- Detects function selectors by searching the deployed bytecode for their
  keccak256 hashes
- Everything runs client-side

**Source: [`../index.html`](../index.html) — 20 KB, readable in one sitting.**

---

## Use it

**Online:** https://mickeentreprise-cell.github.io/ddmx-credit-desk/

**Locally:** download `index.html` and open it. That's it.

**On your own site:** copy `index.html` into your web root.

---

## Tested on

| Token | Result | Score |
|---|---|---|
| **DDMX** `0x90e28b1c…6b53` | PROPRE | 8/10 |
| **USDC** `0x8ac76a51…580d` | PLUTOT SAIN | 8/10 |
| **WBNB** `0xbb4cdb9c…095c` | PROPRE | 8/10 |

DDMX is the token this project deployed. The scanner gives it 8/10, not
10/10, because two checks cannot be answered by static reading. It is not
graded more favourably than anything else.

---

## Limits and honesty

- The selector search is **pattern matching**, not proof. It looks for the
  4-byte signature in the bytecode. A contract could use a different
  signature for the same function, or a proxy could hide it.
- Proxy contracts read as having no owner when the implementation behind
  them does.
- This is **not an audit**. It is a first filter.

---

## License

MIT. Use it, fork it, ship it.
